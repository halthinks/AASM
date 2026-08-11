from __future__ import annotations

from .control_center_v26 import html_document as v26_html_document


_STACK_STYLE = r"""
.aasm-stack{border-color:#365b7d;background:linear-gradient(180deg,#14263a,#0e1824)}.aasm-stack-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.aasm-stack-card{border:1px solid var(--line);border-radius:12px;padding:10px;background:#0b111a}.aasm-stack-card b{display:block;margin-top:4px;overflow-wrap:anywhere}.aasm-stack-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.aasm-stack-note{margin-top:10px;color:var(--muted);font-size:12px}@media(max-width:900px){.aasm-stack-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.aasm-stack-grid{grid-template-columns:1fr}}
"""


_STACK_PANEL = r"""
<section class="panel full aasm-stack"><div class="aasm-kicker">v0.27 One-Command Local Full Stack</div><h2>Local stack</h2><div id="aasmStackStatus" class="empty">Loading PostgreSQL, runtime, worker, and reference-machine state…</div><div class="aasm-stack-grid"><div class="aasm-stack-card"><span class="sub">Live setup machine</span><b id="aasmStackActive">—</b></div><div class="aasm-stack-card"><span class="sub">Completed reference run</span><b id="aasmStackCompleted">—</b></div><div class="aasm-stack-card"><span class="sub">Current machine</span><b id="aasmStackCurrent">—</b></div><div class="aasm-stack-card"><span class="sub">Expected workers</span><b id="aasmStackWorkers">—</b></div></div><div class="aasm-stack-actions"><button onclick="aasmStackLoad('active')">Load live setup</button><button onclick="aasmStackLoad('completed')">Load completed run</button><button onclick="aasmStackReload()">Refresh stack state</button></div><div class="aasm-stack-note">The stack metadata selects existing canonical machines. All machine state still comes from PostgreSQL through the ordinary AASM HTTP and event/reducer path.</div></section>
"""


_STACK_SCRIPT = r"""
<script>
let aasmStackState=null;
function aasmStackMachine(which){if(!aasmStackState)return null;if(which==='active')return aasmStackState.active_machine_id;if(which==='completed')return aasmStackState.completed_machine_id;return aasmStackState.current_machine_id}
async function aasmStackLoad(which){const machine=aasmStackMachine(which);if(!machine)return;$('mid').value=machine;current=machine;await loadDash(true)}
function aasmStackRender(state){aasmStackState=state;$('aasmStackActive').textContent=state.active_machine_id||'—';$('aasmStackCompleted').textContent=state.completed_machine_id||'—';$('aasmStackCurrent').textContent=state.current_machine_id||'—';$('aasmStackWorkers').textContent=[...(state.expected_workers||[]),...(state.optional_workers||[]).map(x=>x+' (optional)')].join(', ')||'—';$('aasmStackStatus').innerHTML=`<span class=good>ready</span> · runtime ${esc(state.runtime_version||'—')} · generation ${esc(state.generation||'—')} · PostgreSQL-backed reference machines`}
function aasmConsumeQueryToken(){const params=new URLSearchParams(location.search);const token=params.get('token');if(token){sessionStorage.setItem('aasmToken',token);$('token').value=token;params.delete('token');const query=params.toString();history.replaceState({},'',location.pathname+(query?'?'+query:'')+location.hash)}return params}
async function aasmStackReload(){try{const state=await api('/demo-stack');aasmStackRender(state);return state}catch(error){$('aasmStackStatus').innerHTML=`<span class=bad>${esc(error.message||error)}</span>`;return null}}
async function aasmStackAutoload(){const params=aasmConsumeQueryToken();const state=await aasmStackReload();if(!state)return;const requested=params.get('machine')||params.get('view');let machine;if(requested==='active'||requested==='completed')machine=aasmStackMachine(requested);else if(requested)machine=requested;else machine=state.current_machine_id||state.active_machine_id;if(machine){$('mid').value=machine;current=machine;await loadDash(true)}}
window.addEventListener('load',()=>{aasmStackAutoload()});
</script>
"""


def html_document() -> str:
    """Extend the existing Control Center with local-stack discovery and selection."""

    page = v26_html_document()
    page = page.replace("</style></head>", _STACK_STYLE + "</style></head>", 1)
    page = page.replace('<div class="grid">', '<div class="grid">' + _STACK_PANEL, 1)
    page = page.replace("</body>", _STACK_SCRIPT + "</body>", 1)
    return page
