// @vitest-environment jsdom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import ManufacturerKnowledge from './ManufacturerKnowledge';

const sha = 'a'.repeat(64);
let writes;
beforeEach(() => {
  writes = [];
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname;
    if (options.method === 'POST') writes.push({path, body: JSON.parse(options.body)});
    const datasets = {
      '/manufacturers': [{id:1,name:'Test manufacturer',verification_status:'pending'}],
      '/equipment-models': [{id:2,manufacturer_id:1,model_name:'Test inverter',equipment_type:'inverter',verification_status:'pending'}],
      '/technical-documents': [{id:3,equipment_model_id:2,title:'Test manual',source_url:'https://example.test/manual',verification_status:'pending'}],
      '/equipment-fault-codes': [{id:4,equipment_model_id:2,fault_code:'F01',description:'Unverified description',verification_status:'pending'}],
      '/manufacturer-knowledge/trusted-fault-codes/2': [],
      '/manufacturer-knowledge/documents/pending-review': {count:1,documents:[{sha256:sha,title:'Pending PDF',source_url:'https://example.test/manual'}],errors:[]},
      [`/manufacturer-knowledge/documents/pending-review/${sha}/audit`]: {pdf_integrity:{valid:true},review_count:0,ready_for_separate_verification:false,issues:['No recorded human review']},
    };
    return {ok:true,status:200,json:async()=>datasets[path] || {verification_status:'pending'}};
  }));
});
afterEach(() => {cleanup();vi.unstubAllGlobals();});

it('shows library to customers without admin controls or unverified fault guidance', async () => {
  render(<ManufacturerKnowledge token="test-token" role="customer" />);
  await screen.findByText('Test manufacturer', {selector:'strong'});
  expect(screen.queryByRole('heading',{name:'Register pending knowledge'})).toBeNull();
  expect(screen.queryByText('Load pending PDFs')).toBeNull();
  expect(fetch.mock.calls.some(([url])=>url.endsWith('/equipment-fault-codes'))).toBe(false);
  fireEvent.change(screen.getByLabelText('Equipment model'),{target:{value:'2'}});
  await screen.findByText('No fault codes with a fully verified evidence chain are available for this model.');
  expect(screen.getByRole('link',{name:'Test manual'}).getAttribute('href')).toBe('https://example.test/manual');
  expect(screen.queryByText('Unverified description')).toBeNull();
});

it('registers a manufacturer as pending without requesting verification', async () => {
  render(<ManufacturerKnowledge token="test-token" role="admin" />);
  await screen.findByText('Test manufacturer', {selector:'strong'});
  fireEvent.click(screen.getByText('Register manufacturer',{selector:'summary'}));
  fireEvent.change(screen.getByLabelText('Manufacturer name'),{target:{value:'New maker'}});
  fireEvent.click(screen.getByRole('button',{name:'Register manufacturer'}));
  await screen.findByText('Registered as pending. Separate evidence review is required.');
  expect(writes).toEqual([{path:'/manufacturers',body:{name:'New maker'}}]);
});

it('sends explicit evidence and note for a selected record review', async () => {
  render(<ManufacturerKnowledge token="test-token" role="admin" />);
  await screen.findByRole('button',{name:'Review Test manufacturer'});
  fireEvent.click(screen.getByRole('button',{name:'Review Test manufacturer'}));
  fireEvent.change(screen.getByLabelText('HTTPS evidence URL'),{target:{value:'https://example.test/manufacturer'}});
  fireEvent.change(screen.getByLabelText('Review note or revocation reason'),{target:{value:'Independently checked official source.'}});
  fireEvent.click(screen.getByRole('button',{name:'Record verification'}));
  await screen.findByText('Verification recorded.');
  expect(writes[0]).toEqual({path:'/manufacturer-knowledge/manufacturer/1/verify',body:{verification_note:'Independently checked official source.',evidence_url:'https://example.test/manufacturer'}});
});

it('records provenance approval without calling database verification', async () => {
  render(<ManufacturerKnowledge token="test-token" role="admin" />);
  await screen.findByText('Test manufacturer', {selector:'strong'});
  fireEvent.click(screen.getByRole('button',{name:'Load pending PDFs'}));
  await screen.findByRole('button',{name:'Pending PDF'});
  fireEvent.click(screen.getByRole('button',{name:'Pending PDF'}));
  await screen.findByLabelText('Provenance decision');
  fireEvent.change(screen.getByLabelText('Provenance decision'),{target:{value:'approve_provenance'}});
  fireEvent.change(screen.getByLabelText('Provenance review note'),{target:{value:'Reviewed the official source and stored document integrity.'}});
  fireEvent.click(screen.getByRole('button',{name:'Record provenance review'}));
  await screen.findByText('Review recorded. Manufacturer database verification was not changed.');
  expect(writes).toHaveLength(1);
  expect(writes[0].path).toBe(`/manufacturer-knowledge/documents/pending-review/${sha}/decision`);
  expect(writes[0].body.decision).toBe('approve_provenance');
});

it('shows unavailable PDF storage without a fake review success', async () => {
  render(<ManufacturerKnowledge token="test-token" role="admin" />);
  await screen.findByText('Test manufacturer', {selector:'strong'});
  fetch.mockImplementationOnce(async()=>({ok:false,status:503,json:async()=>({detail:'Pending PDF storage is not configured'})}));
  fireEvent.click(screen.getByRole('button',{name:'Load pending PDFs'}));
  await screen.findByText('Pending PDF storage is not configured');
  expect(writes).toEqual([]);
});
