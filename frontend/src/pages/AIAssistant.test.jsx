// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import AIAssistant from './AIAssistant';

let cases, messages, profile, payloads;
const reply = () => ({message: 'Read the displayed equipment status.', profile,
  next_questions: ['What is the exact inverter model?'], possible_causes: [],
  recommended_checks: [], suggested_solutions: [], sources: [],
  safety_notice: 'Contact an authorized technician.'});

beforeEach(() => {
  cases = []; messages = []; profile = {}; payloads = [];
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    const path = new URL(url).pathname;
    let data;
    if (options.method === 'POST') {
      const body = JSON.parse(options.body); payloads.push(body);
      if (path.endsWith('/messages')) profile = {...profile, battery_soc_percent: 45, ...body.updates};
      else { profile = body.profile; cases = [{id: 1, title: body.question}]; }
      const response = reply();
      messages.push({role: 'user', content: body.question}, {role: 'assistant', content: response.message, response_metadata: response});
      data = {session_id: 1, response};
    } else if (path.endsWith('/1')) data = {session: {id: 1, equipment_profile: profile}, messages};
    else data = cases;
    return {ok: true, status: 200, json: async () => data};
  }));
});

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

async function start() {
  render(<AIAssistant token="synthetic-token" />);
  await screen.findByText('Your first case will appear here after you send a message.');
  fireEvent.change(screen.getByLabelText('Inverter manufacturer'), {target: {value: 'Reported brand'}});
  fireEvent.change(screen.getByLabelText('Battery charge (%)'), {target: {value: '20'}});
  fireEvent.change(screen.getByLabelText('Describe the fault'), {target: {value: 'Not charging from solar'}});
  fireEvent.click(screen.getByRole('button', {name: 'Start saved conversation'}));
  await screen.findByRole('heading', {name: 'Case #1'});
  await waitFor(() => expect(screen.getByRole('button', {name: 'Send follow-up'}).disabled).toBe(false));
}

describe('saved assistant cases', () => {
  it('creates a case with equipment details and displays safety guidance', async () => {
    await start();
    expect(payloads[0]).toEqual({question: 'Not charging from solar', profile: {inverter_brand: 'Reported brand', battery_soc_percent: 20}});
    expect(screen.getByText('Contact an authorized technician.')).toBeTruthy();
    expect(screen.getByRole('button', {name: 'Not charging from solar'})).toBeTruthy();
  });

  it('sends only edited fields, and reopens the saved conversation', async () => {
    await start();
    fireEvent.change(screen.getByLabelText('Follow-up message'), {target: {value: 'SOC is 45%'}});
    fireEvent.click(screen.getByRole('button', {name: 'Send follow-up'}));
    await screen.findByText('SOC is 45%');
    expect(payloads[1]).toEqual({question: 'SOC is 45%', updates: {}});
    await waitFor(() => expect(screen.getByRole('button', {name: 'New conversation'}).disabled).toBe(false));
    fireEvent.click(screen.getByRole('button', {name: 'New conversation'}));
    expect(screen.getByLabelText('Battery charge (%)').value).toBe('');
    fireEvent.click(screen.getByRole('button', {name: 'Not charging from solar'}));
    await screen.findByRole('heading', {name: 'Case #1'});
    expect(screen.getByLabelText('Battery charge (%)').value).toBe('45');
    expect(screen.getByText('SOC is 45%')).toBeTruthy();
  });

  it('keeps the message when the server rejects it', async () => {
    await start();
    fetch.mockImplementationOnce(async () => ({ok: false, status: 422, json: async () => ({detail: 'Invalid reported reading'})}));
    fireEvent.change(screen.getByLabelText('Follow-up message'), {target: {value: 'New reading'}});
    fireEvent.click(screen.getByRole('button', {name: 'Send follow-up'}));
    await screen.findByText('Invalid reported reading');
    expect(screen.getByLabelText('Follow-up message').value).toBe('New reading');
  });

  it('shows an expired session and supports retrying case loading', async () => {
    fetch.mockImplementationOnce(async () => ({ok: false, status: 401, json: async () => ({})}));
    render(<AIAssistant token="synthetic-token" />);
    await screen.findByText('Your session has expired. Sign in again.');
    fireEvent.click(screen.getByRole('button', {name: 'Retry loading'}));
    await screen.findByText('Your first case will appear here after you send a message.');
  });

  it('rejects whitespace without writing a case', async () => {
    render(<AIAssistant token="synthetic-token" />);
    await screen.findByText('Your first case will appear here after you send a message.');
    fireEvent.change(screen.getByLabelText('Describe the fault'), {target: {value: '    '}});
    fireEvent.click(screen.getByRole('button', {name: 'Start saved conversation'}));
    await screen.findByText('Enter at least two characters describing the problem.');
    expect(payloads).toEqual([]);
  });
});
