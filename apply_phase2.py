from pathlib import Path
root=Path.cwd()
main=root/"backend/app/main.py"
app=root/"frontend/src/App.jsx"
if not main.exists() or not app.exists():
    raise SystemExit("Run in the root of the existing Phase 1 repository.")
s=main.read_text()
anchor="from app.routes import diagnostics, alerts, dashboard"
line="from app.routes.ai_assistant import router as ai_assistant_router"
if line not in s:
    if anchor not in s: raise SystemExit("Unexpected main.py import structure")
    s=s.replace(anchor,anchor+"\n"+line)
anchor="app.include_router(dashboard.router)"
if "app.include_router(ai_assistant_router)" not in s:
    if anchor not in s: raise SystemExit("Unexpected main.py router structure")
    s=s.replace(anchor,anchor+"\napp.include_router(ai_assistant_router)")
main.write_text(s)
s=app.read_text()
anchor='import Devices from "./pages/Devices";'
line='import AIAssistant from "./pages/AIAssistant";'
if line not in s:
    if anchor not in s: raise SystemExit("Unexpected App.jsx import structure")
    s=s.replace(anchor,anchor+"\n"+line)
if 'setActivePage("ai-assistant")' not in s:
    anchor="        </nav>"
    if anchor not in s: raise SystemExit("Unexpected sidebar structure")
    s=s.replace(anchor,'          <button className={activePage === "ai-assistant" ? "active" : ""} onClick={() => setActivePage("ai-assistant")}>AI Assistant</button>\n'+anchor,1)
if 'activePage === "ai-assistant" ? (' not in s:
    anchor='        {activePage === "systems" ? ('
    if anchor not in s: raise SystemExit("Unexpected page structure")
    s=s.replace(anchor,'        {activePage === "ai-assistant" ? (\n          <AIAssistant token={token} />\n        ) : activePage === "systems" ? (',1)
app.write_text(s)
print("Phase 2 assistant integrated. Run tests and review git diff.")
