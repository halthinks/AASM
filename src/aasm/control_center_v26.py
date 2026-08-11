from __future__ import annotations

from .control_center_v19 import html_document as v19_html_document


_EXTRA_STYLE = r"""
.aasm-reasoning .node{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;padding:9px 0;border-bottom:1px solid #1b2635}.aasm-reasoning .node:last-child{border-bottom:0}.aasm-reasoning .label{font-weight:650}.aasm-reasoning .meta{color:var(--muted);font-size:12px}.aasm-reasoning .status{align-self:start;border:1px solid var(--line);border-radius:999px;padding:2px 7px;font-size:11px}.aasm-reasoning .ACTIVE,.aasm-reasoning .COMMITTED,.aasm-reasoning .VERIFIED,.aasm-reasoning .PASS,.aasm-reasoning .RESOLVED{color:var(--good)}.aasm-reasoning .OPEN,.aasm-reasoning .LOCKED,.aasm-reasoning .NEEDS_REVALIDATION,.aasm-reasoning .SOFT{color:var(--warn)}.aasm-reasoning .INVALIDATED,.aasm-reasoning .REJECTED,.aasm-reasoning .FAIL{color:var(--bad)}.aasm-kicker{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin-bottom:6px}.aasm-highlight{border-left:3px solid var(--accent);padding-left:10px}.aasm-stats{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 10px}.aasm-stats span{border:1px solid var(--line);border-radius:999px;padding:3px 8px;color:var(--muted);font-size:12px}.aasm-detail{width:100%;text-align:left;background:transparent;border:0;padding:0;color:inherit}.aasm-detail:hover{color:var(--accent)}
"""


_EXTRA_PANELS = r"""
<section class="panel full aasm-reasoning"><div class="aasm-kicker">v0.26 Research Synthesis Hero Stack</div><h2>Reasoning overview</h2><div id="aasmReasoningSummary" class="empty">Load a machine to inspect decisions, obligations, evidence, conflicts, and provenance.</div></section>
<section class="panel wide aasm-reasoning"><h2>Decision Graph</h2><div id="aasmDecisionStats" class="aasm-stats"></div><div id="aasmDecisions" class="scroll"></div></section>
<section class="panel wide aasm-reasoning"><h2>Obligation Graph</h2><div id="aasmObligationStats" class="aasm-stats"></div><div id="aasmObligations" class="scroll"></div></section>
<section class="panel wide aasm-reasoning"><h2>Evidence Graph</h2><div id="aasmEvidenceStats" class="aasm-stats"></div><div id="aasmEvidence" class="scroll"></div></section>
<section class="panel wide aasm-reasoning"><h2>Conflict · learned no-good · backjump</h2><div id="aasmConflicts" class="scroll"></div></section>
<section class="panel wide aasm-reasoning"><h2>Fairness debt</h2><div id="aasmFairness" class="scroll"></div></section>
<section class="panel wide aasm-reasoning"><h2>Profile and migration history</h2><div id="aasmPackageHistory" class="scroll"></div></section>
<section class="panel full aasm-reasoning"><h2>Final synthesis and provenance</h2><div id="aasmFinalArtifact" class="scroll"></div></section>
"""


_EXTRA_SCRIPT = r"""
<script>
// Stable inspection suffixes: /inspect/decisions /inspect/obligations /inspect/evidence /inspect/conflicts /inspect/fairness /inspect/packages
let aasmReasoning={};
function aasmStatusClass(value){return esc(String(value||'UNKNOWN').toUpperCase())}
function aasmGraphStats(target,graph){const kinds={};for(const n of graph.nodes||[])kinds[n.kind]=(kinds[n.kind]||0)+1;$(target).innerHTML=`<span>${(graph.nodes||[]).length} nodes</span><span>${(graph.edges||[]).length} edges</span>`+Object.entries(kinds).map(([k,v])=>`<span>${esc(k)} ${v}</span>`).join('')}
function aasmNodeRows(items,kind){return rows(items,(node,index)=>`<div class=node><button class=aasm-detail onclick="aasmShowDetail('${kind}',${index})"><span class=label>${esc(node.label||node.id)}</span><br><span class=meta>${esc(node.id)}${node.value!==undefined?' · '+esc(JSON.stringify(node.value)):''}</span></button><span class="status ${aasmStatusClass(node.status)}">${esc(node.status||node.kind||'')}</span></div>`)}
function aasmShowDetail(kind,index){const value=(aasmReasoning[kind]||[])[index];alert(JSON.stringify(value,null,2))}
function aasmRenderSummary(summary){const profile=summary.package_history?.current||{};const active=summary.decision_graph?.metadata?.active_model||{};const conflict=(summary.conflict_timeline||[]).filter(x=>x.type==='CONFLICT_BACKJUMPED').slice(-1)[0];const latest=last?.semantic_results?.latest;$('aasmReasoningSummary').innerHTML=`<div class=aasm-stats><span>state ${esc(summary.machine_state)}</span><span>version ${esc(summary.machine_version)}</span><span>profile ${esc(profile.profile_id||'unbound')}</span><span>active decisions ${Object.keys(active).length}</span><span>evidence ${summary.evidence_graph?.metadata?.record_count||0}</span></div><div class=aasm-highlight><b>${conflict?'Causal recovery completed':'No completed backjump yet'}</b><div class=meta>${conflict?`target ${esc(conflict.backjump?.pivot_decision_id||'—')} · invalidated ${esc((conflict.backjump?.invalidated_decision_ids||[]).join(', ')||'none')}`:'Run or load the research-synthesis reference machine to see conflict learning.'}</div>${latest?`<div class=meta>latest semantic result: ${esc(latest.classification)} · ${esc(latest.summary)}</div>`:''}</div>`}
function aasmRenderConflicts(items){aasmReasoning.conflicts=items;$('aasmConflicts').innerHTML=rows(items,(item,index)=>{const back=item.backjump||{};const detail=item.type==='CONFLICT_BACKJUMPED'?`target ${back.pivot_decision_id||'—'} · invalidated ${(back.invalidated_decision_ids||[]).join(', ')||'none'}`:(item.constraint_id?`${item.constraint_id} · ${item.strength||''}`:(item.explanation_id||item.kind||''));return `<div class=node><button class=aasm-detail onclick="aasmShowDetail('conflicts',${index})"><span class=label>${esc(item.type)}</span><br><span class=meta>${esc(item.conflict_id||'')} · ${esc(detail)}</span></button><span class="status ${aasmStatusClass(item.status||item.strength)}">${esc(item.status||item.strength||'')}</span></div>`})}
function aasmRenderFairness(items){aasmReasoning.fairness=items;$('aasmFairness').innerHTML=rows(items,(item,index)=>`<div class=node><button class=aasm-detail onclick="aasmShowDetail('fairness',${index})"><span class=label>${esc(item.obligation_id)}</span><br><span class=meta>hidden ${item.hidden_epochs||0} · locked ${item.continuous_lock_epochs||0} · next ${esc(item.next_action||'NONE')}</span></button><span class="status ${aasmStatusClass(item.status)}">${esc(item.status)}</span></div>`)}
function aasmRenderPackages(value){const current=value.current||{};const history=value.evolution_history||[];$('aasmPackageHistory').innerHTML=`<div class=node><div><span class=label>${esc(current.profile_id||'No profile bound')}</span><br><span class=meta>${esc(current.profile_version||'')} · ${esc(current.package_id||'')}</span></div><span class="status ${aasmStatusClass(current.status)}">${esc(current.status||'')}</span></div>`+rows(history,(row,index)=>`<div class=node><button class=aasm-detail onclick="aasmShowDetail('packages',${index})"><span class=label>${esc(row.from?.profile_version||'—')} → ${esc(row.to_profile_version||'—')}</span><br><span class=meta>${esc(row.actor||'')} · sequence ${esc(row.sequence||'')}</span></button></div>`);aasmReasoning.packages=history}
function aasmRenderArtifact(){const latest=last?.semantic_results?.latest;if(!latest){$('aasmFinalArtifact').innerHTML='<div class=empty>No final semantic result has been recorded.</div>';return}const artifact=(latest.artifacts||[])[0]||{};const claim=(latest.claims||[])[0]||{};$('aasmFinalArtifact').innerHTML=`<div class=aasm-stats><span>${esc(latest.classification)}</span><span>${esc(artifact.kind||'artifact')}</span><span>${esc(artifact.artifact_id||'')}</span></div><div class=aasm-highlight><b>${esc(claim.claim||latest.summary)}</b><div class=meta>artifact SHA-256 ${esc(artifact.sha256||'—')}</div><div class=meta>evidence ${(claim.evidence_ids||[]).map(esc).join(', ')||'—'}</div></div><pre>${esc(JSON.stringify(latest,null,2))}</pre>`}
async function loadAasmReasoning(){if(!current)return;try{const root='/v1/machines/'+encodeURIComponent(current)+'/inspect/';const [summary,decisions,obligations,evidence,conflicts,fairness,packages]=await Promise.all([api(root+'summary'),api(root+'decisions'),api(root+'obligations'),api(root+'evidence'),api(root+'conflicts'),api(root+'fairness'),api(root+'packages')]);aasmReasoning={summary,decisions:decisions.nodes||[],obligations:obligations.nodes||[],evidence:evidence.nodes||[],conflicts,fairness,packages:packages.evolution_history||[]};aasmRenderSummary(summary);aasmGraphStats('aasmDecisionStats',decisions);aasmGraphStats('aasmObligationStats',obligations);aasmGraphStats('aasmEvidenceStats',evidence);$('aasmDecisions').innerHTML=aasmNodeRows(decisions.nodes||[],'decisions');$('aasmObligations').innerHTML=aasmNodeRows(obligations.nodes||[],'obligations');$('aasmEvidence').innerHTML=aasmNodeRows(evidence.nodes||[],'evidence');aasmRenderConflicts(conflicts);aasmRenderFairness(fairness);aasmRenderPackages(packages);aasmRenderArtifact()}catch(error){$('aasmReasoningSummary').innerHTML=`<span class=bad>${esc(error.message||error)}</span>`}}
const aasmBaseLoadDash=loadDash;
loadDash=async function(reset=true){await aasmBaseLoadDash(reset);await loadAasmReasoning()}
</script>
"""


def html_document() -> str:
    """Extend the proven v0.19 Control Center with v0.26 reasoning views."""

    page = v19_html_document()
    page = page.replace("</style></head>", _EXTRA_STYLE + "</style></head>", 1)
    page = page.replace("</div></main>\n<script>", _EXTRA_PANELS + "</div></main>\n<script>", 1)
    page = page.replace("</body>", _EXTRA_SCRIPT + "</body>", 1)
    return page
