import {useState} from "react";
import {API_BASE_URL} from "../config";
import "./AIAssistant.css";
export default function AIAssistant({token}) {
 const [question,setQuestion]=useState("");
 const [telemetry,setTelemetry]=useState("");
 const [result,setResult]=useState(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function submit(e) {
  e.preventDefault();setBusy(true);setError("");setResult(null);
  try {
   const payload={question};
   if(telemetry.trim()) {
    const n=Number(telemetry);
    if(!Number.isInteger(n)||n<1) throw Error("Invalid telemetry ID");
    payload.telemetry_id=n;
   }
   const res=await fetch(`${API_BASE_URL}/ai-assistant/ask`,{
    method:"POST",headers:{"Content-Type":"application/json",Authorization:`Bearer ${token}`},
    body:JSON.stringify(payload)});
   const data=await res.json();
   if(!res.ok) throw Error(typeof data.detail==="string"?data.detail:"Request failed");
   setResult(data.response);
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <section className="solarai-assistant">
  <h1>SolarAI Troubleshooting Assistant</h1>
  <p>Get safety-conscious advice based on available diagnostic evidence.</p>
  <form onSubmit={submit}>
   <label htmlFor="question">Describe the fault</label>
   <textarea id="question" required minLength={5} maxLength={2000} rows={5} value={question} onChange={e=>setQuestion(e.target.value)}/>
   <label htmlFor="telemetry">Telemetry ID (optional)</label>
   <input id="telemetry" type="number" min="1" value={telemetry} onChange={e=>setTelemetry(e.target.value)}/>
   <button disabled={busy}>{busy?"Analysing...":"Ask SolarAI"}</button>
  </form>
  {error&&<p role="alert">{error}</p>}
  {result&&<article aria-live="polite"><h2>Guidance</h2><small>{result.mode}</small><p className="response">{result.answer}</p>
   <ul>{result.sources.map(s=><li key={s.id}>{s.title} ({s.id})</li>)}</ul></article>}
 </section>
}
