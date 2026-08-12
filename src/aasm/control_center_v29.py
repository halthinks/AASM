from __future__ import annotations

from .control_center_v27 import html_document as v27_html_document


_LANGGRAPH_STYLE = r"""
.aasm-langgraph{border-color:#5367a8;background:linear-gradient(180deg,#171d38,#0e1426)}.aasm-langgraph-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.aasm-langgraph-card{border:1px solid var(--line);border-radius:12px;padding:10px;background:#0b111a}.aasm-langgraph-card b{display:block;margin-top:4px;overflow-wrap:anywhere}.aasm-langgraph pre{max-height:260px}@media(max-width:900px){.aasm-langgraph-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.aasm-langgraph-grid{grid-template-columns:1fr}}
"""


_LANGGRAPH_PANEL = r"""
<section class="panel full aasm-langgraph"><div class="aasm-kicker">v0.29 Thin LangGraph Adapter</div><h2>Adapted run</h2><div id="aasmLangGraphStatus" class="empty">Load a LangGraph-bound AASM machine to inspect the framework boundary.</div><div class="aasm-langgraph-grid"><div class="aasm-langgraph-card"><span class="sub">Thread / run</span><b id="aasmLangGraphThread">—</b></div><div class="aasm-langgraph-card"><span class="sub">Node events</span><b id="aasmLangGraphNodes">—</b></div><div class="aasm-langgraph-card"><span class="sub">Recovery events</span><b id="aasmLangGraphRecoveries">—</b></div><div class="aasm-langgraph-card"><span class="sub">Authority split</span><b id="aasmLangGraphAuthority">—</b></div></div><pre id="aasmLangGraphDetail">No adapted run loaded.</pre></section>
"""


_LANGGRAPH_SCRIPT = r"""
<script>
function aasmRenderLangGraph(value){const binding=value.binding||{};const run=binding.binding||{};$('aasmLangGraphThread').textContent=[run.thread_id||'—',run.run_id||''].filter(Boolean).join(' / ');$('aasmLangGraphNodes').textContent=String((value.node_events||[]).length);$('aasmLangGraphRecoveries').textContent=String((value.recovery_events||[]).length);$('aasmLangGraphAuthority').textContent='LangGraph checkpoints · AASM truth';$('aasmLangGraphStatus').innerHTML=`<span class=good>bound</span> · ${esc(value.adapter_id||'aasm.langgraph.v1')} ${esc(value.adapter_version||'')} · replay ${value.replay_snapshot_hash===value.persisted_snapshot_hash?'exact':'mismatch'}`;$('aasmLangGraphDetail').textContent=JSON.stringify(value,null,2)}
async function loadAasmLangGraph(){if(!current)return;try{const value=await api('/v1/machines/'+encodeURIComponent(current)+'/inspect/langgraph');aasmRenderLangGraph(value)}catch(error){$('aasmLangGraphStatus').innerHTML=`<span class=muted>not a LangGraph-bound machine</span> · ${esc(error.message||error)}`;$('aasmLangGraphThread').textContent='—';$('aasmLangGraphNodes').textContent='—';$('aasmLangGraphRecoveries').textContent='—';$('aasmLangGraphAuthority').textContent='—';$('aasmLangGraphDetail').textContent='No adapted run loaded.'}}
const aasmV29BaseLoadDash=loadDash;
loadDash=async function(reset=true){await aasmV29BaseLoadDash(reset);await loadAasmLangGraph()}
</script>
"""


def html_document() -> str:
    """Add a LangGraph boundary view without changing the established dashboard."""

    page = v27_html_document()
    page = page.replace("</style></head>", _LANGGRAPH_STYLE + "</style></head>", 1)
    page = page.replace('<div class="grid">', '<div class="grid">' + _LANGGRAPH_PANEL, 1)
    page = page.replace("</body>", _LANGGRAPH_SCRIPT + "</body>", 1)
    return page
