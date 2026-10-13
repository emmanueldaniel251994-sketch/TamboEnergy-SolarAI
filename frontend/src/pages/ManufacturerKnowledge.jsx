import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';
import './ManufacturerKnowledge.css';

function Source({ url, title = 'Open source' }) {
  return /^https?:\/\//i.test(url || '') ? <a href={url} target="_blank" rel="noopener noreferrer">{title}</a> : <span>No source link</span>;
}

function RegistrationForm({ title, endpoint, fields, api, refresh }) {
  const [values, setValues] = useState({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      const body = {};
      for (const field of fields) {
        const value = String(values[field.key] || '').trim();
        if (value) body[field.key] = field.numeric ? Number(value) : value;
      }
      await api(endpoint, { method: 'POST', body: JSON.stringify(body) });
      setValues({}); setMessage('Registered as pending. Separate evidence review is required.');
      await refresh();
    } catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  return <details><summary>{title}</summary><form onSubmit={submit}>
    {fields.map(field => <label key={field.key}>{field.label}
      {field.options ? <select required disabled={busy} value={values[field.key] || ''} onChange={e => setValues(v => ({...v, [field.key]: e.target.value}))}>
        <option value="">Select…</option>{field.options.map(option => <option key={option.id} value={option.id}>{option.label}</option>)}
      </select> : field.multiline ? <textarea required={!field.optional} disabled={busy} minLength={field.minLength} maxLength={field.maxLength || 5000}
        value={values[field.key] || ''} onChange={e => setValues(v => ({...v, [field.key]: e.target.value}))} /> : <input required={!field.optional} disabled={busy} type={field.type || 'text'} minLength={field.minLength} maxLength={field.maxLength || 1000}
        value={values[field.key] || ''} onChange={e => setValues(v => ({...v, [field.key]: e.target.value}))} />}
    </label>)}
    <button disabled={busy}>{busy ? 'Saving…' : title}</button>{message && <p role="status">{message}</p>}
  </form></details>;
}

function Verification({ api, target, close, refresh }) {
  const [note, setNote] = useState('');
  const [evidence, setEvidence] = useState(target.source_url || '');
  const [action, setAction] = useState('verify');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      await api(`/manufacturer-knowledge/${target.kind}/${target.id}/${action}`, {
        method: 'POST', body: JSON.stringify(action === 'verify' ? {verification_note: note.trim(), evidence_url: evidence.trim()} : {reason: note.trim()}),
      });
      setMessage(action === 'verify' ? 'Verification recorded.' : 'Verification revoked, including dependent records.');
      await refresh();
    } catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  return <section className="knowledge-panel" aria-label="Evidence verification">
    <h2>Review: {target.label}</h2>
    <p>Verify manufacturer identity first, then the model, document, and fault code. A provenance journal approval does not verify these records.</p>
    <form onSubmit={submit}>
      <label>Review action<select value={action} disabled={busy} onChange={e => setAction(e.target.value)}>
        <option value="verify">Verify using independent evidence</option><option value="revoke">Revoke verification</option>
      </select></label>
      {action === 'verify' ? <label>HTTPS evidence URL<input required type="url" pattern="https://.*" maxLength={1000} value={evidence} disabled={busy} onChange={e => setEvidence(e.target.value)} /></label>
        : <p>Revoking this record also revokes dependent models, documents, or fault codes.</p>}
      <label>Review note or revocation reason<textarea required minLength={10} maxLength={2000} value={note} disabled={busy} onChange={e => setNote(e.target.value)} /></label>
      <button disabled={busy}>{busy ? 'Recording…' : action === 'verify' ? 'Record verification' : 'Revoke record and dependents'}</button>
      <button type="button" disabled={busy} onClick={close}>Close review</button>
      {message && <p role="status">{message}</p>}
    </form>
  </section>;
}

function PendingReviews({ api }) {
  const [inventory, setInventory] = useState(null);
  const [selected, setSelected] = useState(null);
  const [audit, setAudit] = useState(null);
  const [decision, setDecision] = useState('needs_more_evidence');
  const [note, setNote] = useState('');
  const [evidence, setEvidence] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  async function load(document = null) {
    setBusy(true); setMessage('');
    try {
      if (document) {
        const result = await api(`/manufacturer-knowledge/documents/pending-review/${document.sha256}/audit`);
        setSelected(document); setAudit(result); setEvidence(document.source_url || ''); setNote(''); setDecision('needs_more_evidence');
      } else setInventory(await api('/manufacturer-knowledge/documents/pending-review'));
    } catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  async function submit(event) {
    event.preventDefault(); setBusy(true); setMessage('');
    try {
      await api(`/manufacturer-knowledge/documents/pending-review/${selected.sha256}/decision`, {
        method: 'POST', body: JSON.stringify({decision, note: note.trim(), evidence_url: evidence.trim() || null}),
      });
      setAudit(await api(`/manufacturer-knowledge/documents/pending-review/${selected.sha256}/audit`));
      setMessage('Review recorded. Manufacturer database verification was not changed.'); setNote('');
    } catch (err) { setMessage(err.message); }
    finally { setBusy(false); }
  }
  return <section className="knowledge-panel">
    <h2>Pending PDF provenance reviews</h2>
    <p>A matching file hash confirms stored bytes, not publisher authenticity. Approval records provenance review only.</p>
    <button disabled={busy} onClick={() => load()}>{busy ? 'Loading…' : 'Load pending PDFs'}</button>
    {inventory && <><p>{inventory.count} documents in this view.</p>
      <ul>{inventory.documents.map(document => <li key={document.sha256}><button disabled={busy} onClick={() => load(document)}>{document.title || document.sha256}</button></li>)}</ul>
      {inventory.errors?.length > 0 && <p role="alert">{inventory.errors.length} files failed integrity review. Review the storage records before continuing.</p>}
    </>}
    {selected && audit && <div>
      <h3>{selected.title}</h3><Source url={selected.source_url} />
      <p>PDF integrity: {audit.pdf_integrity.valid ? 'Confirmed' : 'Not confirmed'} · Reviews: {audit.review_count}</p>
      <p>{audit.ready_for_separate_verification ? 'Ready for a separate verification review.' : 'Not ready for separate verification.'}</p>
      {audit.issues?.length > 0 && <ul>{audit.issues.map(issue => <li key={issue}>{issue}</li>)}</ul>}
      {audit.latest_review && <p>Latest decision: {audit.latest_review.decision} — {audit.latest_review.note}</p>}
      <form onSubmit={submit}>
        <label>Provenance decision<select disabled={busy} value={decision} onChange={e => setDecision(e.target.value)}>
          <option value="needs_more_evidence">Needs more evidence</option><option value="reject">Reject</option><option value="approve_provenance">Approve provenance only</option>
        </select></label>
        <label>Provenance evidence URL<input disabled={busy} required={decision === 'approve_provenance'} type="url" pattern="https://.*" maxLength={2048} value={evidence} onChange={e => setEvidence(e.target.value)} /></label>
        <label>Provenance review note<textarea disabled={busy} required minLength={20} maxLength={2000} value={note} onChange={e => setNote(e.target.value)} /></label>
        <button disabled={busy || !audit.pdf_integrity.valid}>Record provenance review</button>
      </form>
    </div>}
    {message && <p role="status">{message}</p>}
  </section>;
}

export default function ManufacturerKnowledge({ token, role }) {
  const admin = role === 'admin';
  const [registry, setRegistry] = useState({manufacturers: [], models: [], documents: [], faults: []});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modelId, setModelId] = useState('');
  const [trusted, setTrusted] = useState(null);
  const [lookupError, setLookupError] = useState('');
  const [target, setTarget] = useState(null);
  const api = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API_BASE_URL}${path}`, {...options, headers: {'Content-Type': 'application/json', Authorization: `Bearer ${token}`}});
    const data = await response.json().catch(() => null);
    if (!response.ok) throw Error(response.status === 401 ? 'Your session has expired. Sign in again.' : typeof data?.detail === 'string' ? data.detail : 'Unable to complete the knowledge request.');
    if (data === null) throw Error('Unreadable server response.');
    return data;
  }, [token]);
  const refresh = useCallback(async (signal) => {
    setLoading(true); setError('');
    try {
      const [manufacturers, models, documents, faults] = await Promise.all([
        api('/manufacturers', {signal}), api('/equipment-models', {signal}), api('/technical-documents', {signal}),
        admin ? api('/equipment-fault-codes', {signal}) : Promise.resolve([]),
      ]);
      if (!signal?.aborted) setRegistry({manufacturers, models, documents, faults});
    } catch (err) { if (!signal?.aborted) setError(err.message); }
    finally { if (!signal?.aborted) setLoading(false); }
  }, [api, admin]);
  useEffect(() => {
    const controller = new AbortController();
    Promise.resolve().then(() => { if (!controller.signal.aborted) refresh(controller.signal); });
    return () => controller.abort();
  }, [refresh]);
  useEffect(() => {
    if (!modelId) return;
    const controller = new AbortController();
    api(`/manufacturer-knowledge/trusted-fault-codes/${modelId}`, {signal: controller.signal}).then(data => {
      if (!controller.signal.aborted) { setTrusted(data); setLookupError(''); }
    }).catch(err => { if (!controller.signal.aborted) setLookupError(err.message); });
    return () => controller.abort();
  }, [modelId, api, registry]);
  function review(kind, record, label) { setTarget({...record, kind, label}); }
  const options = registry.models.map(model => ({id: model.id, label: model.model_name}));
  return <section className="manufacturer-knowledge">
    <h1>Equipment knowledge library</h1>
    <p>Browse manufacturer records and source documents. Pending or revoked records are not verified guidance.</p>
    {loading && <p role="status">Loading knowledge records…</p>}
    {error && <p role="alert">{error}</p>}
    <button disabled={loading} onClick={() => refresh()}>Refresh knowledge</button>
    <section className="knowledge-panel"><h2>Manufacturers</h2>
      <ul>{registry.manufacturers.map(record => <li key={record.id}><strong>{record.name}</strong> — {record.verification_status} {admin && <button onClick={() => review('manufacturer', record, record.name)}>Review {record.name}</button>}</li>)}</ul>
      {!loading && registry.manufacturers.length === 0 && <p>No manufacturer records available.</p>}
    </section>
    <section className="knowledge-panel"><h2>Equipment models</h2>
      <label>Equipment model<select value={modelId} onChange={e => {setModelId(e.target.value); setTrusted(null); setLookupError('');}}><option value="">Choose a model…</option>
        {registry.models.map(model => <option key={model.id} value={model.id}>{model.model_name} ({model.verification_status})</option>)}
      </select></label>
      {modelId && registry.models.filter(model => model.id === Number(modelId)).map(model => <div key={model.id}>
        <p>{model.equipment_type} · {model.verification_status}</p>
        {admin && <button onClick={() => review('equipment_model', model, model.model_name)}>Review model</button>}
      </div>)}
      {modelId && <><h3>Source documents</h3><ul>{registry.documents.filter(doc => doc.equipment_model_id === Number(modelId)).map(doc => <li key={doc.id}>
        <Source url={doc.source_url} title={doc.title} /> — {doc.verification_status}{doc.document_version && ` · Version ${doc.document_version}`}
        {admin && <button onClick={() => review('technical_document', doc, doc.title)}>Review document {doc.id}</button>}
      </li>)}</ul><h3>Verified fault codes</h3>
        {lookupError ? <p role="alert">{lookupError}</p> : trusted === null ? <p>Loading verified fault codes…</p> : trusted.length === 0 ? <p>No fault codes with a fully verified evidence chain are available for this model.</p> : <ul>{trusted.map(fault => <li key={fault.id}><strong>{fault.fault_code}</strong> — {fault.description} · {fault.severity}</li>)}</ul>}
      </>}
    </section>
    {admin && <><section className="knowledge-panel"><h2>Register pending knowledge</h2>
      <RegistrationForm title="Register manufacturer" endpoint="/manufacturers" api={api} refresh={refresh} fields={[
        {key:'name',label:'Manufacturer name',minLength:2,maxLength:150}, {key:'official_website',label:'Official website',type:'url',optional:true,maxLength:500},
      ]} />
      <RegistrationForm title="Register model" endpoint="/equipment-models" api={api} refresh={refresh} fields={[
        {key:'manufacturer_id',label:'Manufacturer',numeric:true,options:registry.manufacturers.map(m=>({id:m.id,label:m.name}))},
        {key:'model_name',label:'Model name',minLength:2,maxLength:200}, {key:'equipment_type',label:'Equipment type',minLength:2,maxLength:100},
      ]} />
      <RegistrationForm title="Register document link" endpoint="/technical-documents" api={api} refresh={refresh} fields={[
        {key:'equipment_model_id',label:'Document equipment model',numeric:true,options}, {key:'title',label:'Document title',minLength:2,maxLength:300},
        {key:'document_type',label:'Document type',minLength:2,maxLength:100}, {key:'source_url',label:'Document source URL',type:'url'},
        {key:'document_version',label:'Document version',optional:true,maxLength:100},
      ]} />
      <RegistrationForm title="Register fault code" endpoint="/equipment-fault-codes" api={api} refresh={refresh} fields={[
        {key:'equipment_model_id',label:'Fault equipment model',numeric:true,options},
        {key:'source_document_id',label:'Fault source document',numeric:true,options:registry.documents.map(d=>({id:d.id,label:d.title}))},
        {key:'fault_code',label:'Fault code',minLength:1,maxLength:100},
        {key:'description',label:'Fault description',multiline:true,minLength:3,maxLength:5000},
        {key:'recommended_action',label:'Manufacturer recommended action',multiline:true,optional:true,maxLength:5000},
      ]} />
      <h3>Registered fault codes</h3><ul>{registry.faults.filter(f => !modelId || f.equipment_model_id === Number(modelId)).map(f => <li key={f.id}>{f.fault_code} — {f.verification_status} <button onClick={() => review('fault_code', f, f.fault_code)}>Review fault code {f.id}</button></li>)}</ul>
    </section>
      {target && <Verification key={`${target.kind}-${target.id}`} target={target} api={api} refresh={refresh} close={() => setTarget(null)} />}
      <PendingReviews api={api} />
    </>}
  </section>;
}
