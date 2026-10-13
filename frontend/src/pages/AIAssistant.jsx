import { useEffect, useRef, useState } from "react";
import { API_BASE_URL } from "../config";
import TelemetryAdvice from "./TelemetryAdvice";
import "./AIAssistant.css";

const fields = [
  ["equipment_model_id", "Registered equipment for fault-code lookup", 1],
  ["inverter_brand", "Inverter manufacturer"],
  ["inverter_model", "Inverter model"],
  ["battery_technology", "Battery chemistry"],
  ["battery_model", "Battery model"],
  ["fault_code", "Fault or warning code"],
  ["battery_soc_percent", "Battery charge (%)", 0, 100],
  ["pv_voltage_v", "PV voltage (V)", 0],
  ["pv_power_w", "PV power (W)", 0],
];

function Guidance({ result }) {
  if (!result) return null;
  return <div className="assistant-guidance">
    {result.manufacturer_evidence && <section className="assistant-manufacturer-evidence">
      <h3>Manufacturer evidence</h3>
      <p>{result.manufacturer_evidence.message}</p>
      {result.manufacturer_evidence.grounded && <>
        <p><strong>{result.manufacturer_evidence.manufacturer_name} · {result.manufacturer_evidence.model_name}</strong></p>
        <p>Code: {result.manufacturer_evidence.fault_code} · Checked: {result.manufacturer_evidence.checked_at}</p>
        <ul>{result.manufacturer_evidence.matches.map((match, index) => <li key={index}>
          {match.description}{match.description_truncated && " (excerpt)"} · {match.severity}
        </li>)}</ul>
        <ul>{result.manufacturer_evidence.sources.map((source, index) => <li key={index}>
          {/^https?:\/\//i.test(source.source_url || "") ? <a href={source.source_url} target="_blank" rel="noopener noreferrer">{source.title}</a> : source.title}
          {source.document_version && ` · Version ${source.document_version}`}
        </li>)}</ul>
        <p>{result.manufacturer_evidence.safety_notice}</p>
      </>}
    </section>}
    {result.safety_notice && <p className="assistant-safety"><strong>Safety: </strong>{result.safety_notice}</p>}
    {[
      ["next_questions", "Next questions"],
      ["possible_causes", "Possible causes"],
      ["recommended_checks", "Recommended checks"],
      ["suggested_solutions", "Suggested solutions"],
    ].map(([key, title]) => result[key]?.length > 0 && <div key={key}>
      <h3>{title}</h3><ul>{result[key].map((item, index) => <li key={index}>{item}</li>)}</ul>
    </div>)}
    {result.sources?.length > 0 && <div><h3>Evidence references</h3><ul>{result.sources.map((source, index) => {
      const url = source.source_url || source.url;
      return <li key={index}>{/^https?:\/\//i.test(url || "")
        ? <a href={url} target="_blank" rel="noopener noreferrer">{source.title || source.id || "Source"}</a>
        : source.title || source.id || "Source reference"}</li>;
    })}</ul></div>}
  </div>;
}

export default function AIAssistant({ token }) {
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [profile, setProfile] = useState({});
  const [updates, setUpdates] = useState({});
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [busy, setBusy] = useState(false);
  const [listing, setListing] = useState(true);
  const [models, setModels] = useState([]);
  const [modelError, setModelError] = useState("");
  const active = useRef(true);
  const inFlight = useRef(false);

  async function request(path = "", options = {}) {
    const res = await fetch(`${API_BASE_URL}/ai-assistant/sessions${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      if (res.status === 401) throw Error("Your session has expired. Sign in again.");
      throw Error(typeof data?.detail === "string" ? data.detail : "Unable to complete the request. Please try again.");
    }
    if (data === null) throw Error("The server returned an unreadable response.");
    return data;
  }

  async function refreshSessions() {
    setListing(true);
    try {
      const data = await request();
      if (active.current) { setSessions(data); setListError(""); }
    } catch (err) {
      if (active.current) setListError(err.message);
    } finally {
      if (active.current) setListing(false);
    }
  }

  useEffect(() => {
    active.current = true;
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/ai-assistant/sessions`, {
      signal: controller.signal, headers: { Authorization: `Bearer ${token}` },
    }).then(async res => {
      if (!res.ok) throw Error(res.status === 401 ? "Your session has expired. Sign in again." : "Unable to load saved conversations.");
      const data = await res.json();
      if (!controller.signal.aborted) { setSessions(data); setListError(""); }
    }).catch(err => {
      if (!controller.signal.aborted) setListError(err.message);
    }).finally(() => {
      if (!controller.signal.aborted) setListing(false);
    });
    fetch(`${API_BASE_URL}/equipment-models`, {
      signal: controller.signal, headers: { Authorization: `Bearer ${token}` },
    }).then(async res => {
      if (!res.ok) throw Error("Registered models could not be loaded. General guidance remains available.");
      const data = await res.json();
      if (!controller.signal.aborted) { setModels(data); setModelError(""); }
    }).catch(err => { if (!controller.signal.aborted) setModelError(err.message); });
    return () => { active.current = false; controller.abort(); };
  }, [token]);

  function newConversation() {
    if (inFlight.current) return;
    setSessionId(null); setMessages([]); setProfile({}); setUpdates({}); setQuestion(""); setError("");
  }

  async function openSession(id) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const data = await request(`/${id}`);
      if (!active.current) return;
      setSessionId(data.session.id); setMessages(data.messages);
      setProfile(data.session.equipment_profile); setUpdates({}); setQuestion("");
    } catch (err) {
      if (active.current) setError(err.message);
    } finally {
      inFlight.current = false;
      if (active.current) setBusy(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (inFlight.current) return;
    const text = question.trim();
    if (text.length < 2) { setError("Enter at least two characters describing the problem."); return; }
    // Send only edited fields so saved readings never override newly extracted measurements.
    const changes = {};
    for (const [key, , min, max] of fields) {
      if (key === "equipment_model_id" && key in updates && updates[key] === "") { changes[key] = null; continue; }
      if (!(key in updates) || String(updates[key]).trim() === "") continue;
      if (min === undefined) changes[key] = updates[key].trim();
      else {
        const value = Number(updates[key]);
        if (!Number.isFinite(value) || value < min || (max !== undefined && value > max)) {
          setError("Check the equipment measurements before sending."); return;
        }
        changes[key] = value;
      }
    }
    inFlight.current = true; setBusy(true); setError("");
    try {
      const data = await request(sessionId ? `/${sessionId}/messages` : "", {
        method: "POST", body: JSON.stringify(sessionId ? { question: text, updates: changes } : { question: text, profile: changes }),
      });
      if (!active.current) return;
      setSessionId(data.session_id);
      setProfile(data.response.profile); setUpdates({}); setQuestion("");
      setMessages(previous => [...previous,
        { role: "user", content: text },
        { role: "assistant", content: data.response.message, response_metadata: data.response },
      ]);
      await refreshSessions();
    } catch (err) {
      if (active.current) setError(err.message);
    } finally {
      inFlight.current = false;
      if (active.current) setBusy(false);
    }
  }

  return <section className="solarai-assistant">
    <h1>SolarAI Troubleshooting Assistant</h1>
    <p>Keep equipment details and follow-up messages together in a saved case.</p>
    <p className="assistant-safety">Decision support only. For smoke, sparks, or immediate danger, move away and contact emergency services or an authorized technician.</p>
    <div className="assistant-layout">
      <aside className="assistant-history" aria-label="Saved conversations">
        <button type="button" disabled={busy} onClick={newConversation}>New conversation</button>
        <h2>Saved cases</h2>
        {listing && <p role="status">Loading cases…</p>}
        {listError && <div role="alert"><p>{listError}</p><button type="button" disabled={listing || busy} onClick={refreshSessions}>Retry loading</button></div>}
        {!listing && !listError && sessions.length === 0 && <p>Your first case will appear here after you send a message.</p>}
        <ul>{sessions.map(session => <li key={session.id}><button type="button" disabled={busy}
          aria-current={session.id === sessionId ? "true" : undefined} onClick={() => openSession(session.id)}>{session.title}</button></li>)}</ul>
      </aside>
      <div className="assistant-case">
        <h2>{sessionId ? `Case #${sessionId}` : "New case"}</h2>
        <div className="assistant-messages" role="log" aria-label="Conversation" aria-live="polite" aria-relevant="additions">
          {messages.map((message, index) => <article key={message.id || `new-${index}`} className={`assistant-message assistant-${message.role}`}>
            <strong>{message.role === "user" ? "You" : "SolarAI"}</strong>
            {message.response_metadata?.manufacturer_evidence && <h3>General guidance</h3>}
            <p className="response">{message.content}</p>
            {message.role === "assistant" && <Guidance result={message.response_metadata} />}
          </article>)}
        </div>
        <form onSubmit={submit} aria-busy={busy}>
          <fieldset disabled={busy}>
            <legend>Equipment details (optional)</legend>
            <p>Leave unknown values empty. Enter only reported readings; these details are not manufacturer verification.</p>
            <p>Select the exact registered equipment model and enter its exact fault code to request manufacturer evidence. Evidence is rechecked when you reopen the case or send a message.</p>
            {modelError && <p role="status">{modelError}</p>}
            <div className="assistant-equipment">{fields.map(([key, label, min, max]) => <label key={key} htmlFor={`equipment-${key}`}>
              {label}{key === "equipment_model_id" ? <select id={`equipment-${key}`} value={updates[key] ?? profile[key] ?? ""}
                onChange={event => setUpdates(previous => ({ ...previous, [key]: event.target.value }))}>
                <option value="">General guidance / no registered model</option>
                {(updates[key] ?? profile[key]) && !models.some(model => model.id === Number(updates[key] ?? profile[key])) && <option value={updates[key] ?? profile[key]}>Saved model #{updates[key] ?? profile[key]}</option>}
                {models.map(model => <option key={model.id} value={model.id}>{model.model_name} · {model.equipment_type} · #{model.id}</option>)}
              </select> : <input id={`equipment-${key}`} type={min === undefined ? "text" : "number"}
                min={min} max={max} step={min === undefined ? undefined : "any"}
                maxLength={key === "fault_code" ? 100 : key === "battery_technology" ? 100 : 120}
                value={updates[key] ?? profile[key] ?? ""}
                onChange={event => setUpdates(previous => ({ ...previous, [key]: event.target.value }))} />}
            </label>)}</div>
          </fieldset>
          <label htmlFor="question">{sessionId ? "Follow-up message" : "Describe the fault"}</label>
          <textarea id="question" required minLength={2} maxLength={2000} rows={4} disabled={busy}
            value={question} onChange={event => setQuestion(event.target.value)} placeholder="For example: My inverter is not charging from solar." />
          <button disabled={busy}>{busy ? "Please wait…" : sessionId ? "Send follow-up" : "Start saved conversation"}</button>
          {error && <p role="alert">{error}</p>}
        </form>
      </div>
    </div>
    <details className="assistant-legacy"><summary>Ask about a telemetry record</summary><TelemetryAdvice token={token} /></details>
  </section>;
}
