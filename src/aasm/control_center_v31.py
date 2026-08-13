from __future__ import annotations

from .control_center_v30 import html_document as v30_html_document


_SCOPE_STYLE = r"""
.aasm-scopes{border-color:#8b6b3d;background:linear-gradient(180deg,#2a2114,#15110b)}.aasm-scope-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.aasm-scope-card{border:1px solid var(--line);border-radius:12px;padding:10px;background:#171109}.aasm-scope-card b{display:block;margin-top:4px;overflow-wrap:anywhere}.aasm-scope-tree{max-height:360px;overflow:auto}.aasm-scope-row{display:grid;grid-template-columns:minmax(140px,1.2fr) repeat(4,minmax(90px,.7fr));gap:8px;padding:8px;border-bottom:1px solid var(--line);align-items:center}.aasm-scope-row code{white-space:normal;overflow-wrap:anywhere}@media(max-width:1000px){.aasm-scope-grid{grid-template-columns:repeat(2,1fr)}.aasm-scope-row{grid-template-columns:1fr 1fr}}@media(max-width:560px){.aasm-scope-grid{grid-template-columns:1fr}.aasm-scope-row{grid-template-columns:1fr}}
"""


_SCOPE_PANEL = r"""
<section class="panel full aasm-scopes"><div class="aasm-kicker">v0.31 Hierarchical Decision Scopes</div><h2>One machine, multiple reasoning levels</h2><p class="sub">Strategy, architecture, implementation, and workstream scopes share one event history and one causal graph. Local overrides are explicit; cross-scope flow is recorded; scoped restart preserves parents and unrelated siblings.</p><div id="aasmScopeStatus" class="empty">Load a machine to inspect its scope hierarchy.</div><div class="aasm-scope-grid"><div class="aasm-scope-card"><span class="sub">Scopes</span><b id="aasmScopeCount">—</b></div><div class="aasm-scope-card"><span class="sub">Dependencies</span><b id="aasmScopeDependencies">—</b></div><div class="aasm-scope-card"><span class="sub">Active scopes</span><b id="aasmScopeActive">—</b></div><div class="aasm-scope-card"><span class="sub">Fairness overdue</span><b id="aasmScopeOverdue">—</b></div><div class="aasm-scope-card"><span class="sub">Migration</span><b id="aasmScopeMigration">—</b></div></div><div id="aasmScopeTree" class="aasm-scope-tree"><div class="empty">No scope report loaded.</div></div><pre id="aasmScopeDetail">Scope dependencies and effective inherited models will appear here.</pre></section>
"""


_SCOPE_SCRIPT = r"""
<script>
function aasmScopeDepth(rows,id){let depth=0;const by=Object.fromEntries(rows.map(row=>[row.scope_id,row]));let current=by[id];const seen=new Set();while(current&&current.parent_scope_id){if(seen.has(current.scope_id))break;seen.add(current.scope_id);depth++;current=by[current.parent_scope_id]}return depth}
function aasmRenderScopes(value){const rows=value.scopes||[];const active=rows.filter(row=>row.status==='ACTIVE').length;const overdue=rows.reduce((n,row)=>n+(((row.fairness_debt||{}).overdue||[]).length),0);$('aasmScopeCount').textContent=String(value.scope_count||rows.length);$('aasmScopeDependencies').textContent=String(value.dependency_count||0);$('aasmScopeActive').textContent=String(active);$('aasmScopeOverdue').textContent=String(overdue);$('aasmScopeMigration').textContent=((value.migration||{}).legacy_flat_state_migrated?'flat → root':'native');$('aasmScopeStatus').innerHTML=`<span class=good>${esc(value.contract_id||'aasm.scopes.v1')}</span> · ${esc(value.contract_version||'')} · one authoritative machine`;const ordered=[...rows].sort((a,b)=>a.scope_id.localeCompare(b.scope_id));$('aasmScopeTree').innerHTML=ordered.map(row=>{const depth=aasmScopeDepth(rows,row.scope_id);const model=Object.keys(row.effective_active_model||{}).length;const counts=row.object_counts||{};return `<div class="aasm-scope-row"><code style="padding-left:${depth*16}px">${esc(row.scope_id)}<br><span class=muted>${esc(row.kind)} · ${esc(row.status)}</span></code><span>local ${Object.keys(row.local_active_model||{}).length}<br><span class=muted>effective ${model}</span></span><span>decisions ${counts.decisions||0}<br><span class=muted>obligations ${counts.obligations||0}</span></span><span>children ${(row.descendant_scope_ids||[]).length}<br><span class=muted>ancestors ${(row.ancestor_scope_ids||[]).length}</span></span><span>overdue ${((row.fairness_debt||{}).overdue||[]).length}</span></div>`}).join('')||'<div class=empty>No scopes.</div>';$('aasmScopeDetail').textContent=JSON.stringify({dependencies:value.dependencies||[],scopes:rows.map(row=>({scope_id:row.scope_id,parent_scope_id:row.parent_scope_id,local_active_model:row.local_active_model,effective_active_model:row.effective_active_model,fairness_debt:row.fairness_debt}))},null,2)}
async function loadAasmScopes(){if(!current)return;try{const value=await api('/v1/machines/'+encodeURIComponent(current)+'/inspect/scopes');aasmRenderScopes(value)}catch(error){$('aasmScopeStatus').innerHTML=`<span class=bad>scope view failed</span> · ${esc(error.message||error)}`}}
const aasmV31BaseLoadDash=loadDash;
loadDash=async function(reset=true){await aasmV31BaseLoadDash(reset);await loadAasmScopes()}
</script>
"""


def html_document() -> str:
    page = v30_html_document()
    page = page.replace("</style></head>", _SCOPE_STYLE + "</style></head>", 1)
    page = page.replace('<div class="grid">', '<div class="grid">' + _SCOPE_PANEL, 1)
    page = page.replace("</body>", _SCOPE_SCRIPT + "</body>", 1)
    return page
