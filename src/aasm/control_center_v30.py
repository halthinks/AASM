from __future__ import annotations

from .control_center_v29 import html_document as v29_html_document


_CONFORMANCE_STYLE = r"""
.aasm-conformance{border-color:#3d8b72;background:linear-gradient(180deg,#102922,#0b1714)}.aasm-conformance-actions{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.aasm-conformance-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.aasm-conformance-card{border:1px solid var(--line);border-radius:12px;padding:10px;background:#091411}.aasm-conformance-card b{display:block;margin-top:4px;overflow-wrap:anywhere}.aasm-conformance pre{max-height:320px}@media(max-width:900px){.aasm-conformance-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.aasm-conformance-grid{grid-template-columns:1fr}}
"""


_CONFORMANCE_PANEL = r"""
<section class="panel full aasm-conformance"><div class="aasm-kicker">v0.30 Adapter Conformance Kit</div><h2>Prove an integration preserves the AASM boundary</h2><p class="sub">Runs black-box authority, evidence, conflict, recovery, replay, lease, effect, and fork scenarios. This is a conformance hook, not a sandbox for untrusted adapter code. <code>CONFORMANCE_HOOK_NOT_SANDBOX</code></p><div class="aasm-conformance-actions"><button onclick="runAasmAdapterConformance('langgraph')">Run LangGraph conformance</button></div><div id="aasmConformanceStatus" class="empty">No conformance report loaded.</div><div class="aasm-conformance-grid"><div class="aasm-conformance-card"><span class="sub">Overall</span><b id="aasmConformanceOverall">—</b></div><div class="aasm-conformance-card"><span class="sub">Passed</span><b id="aasmConformancePassed">—</b></div><div class="aasm-conformance-card"><span class="sub">Failed</span><b id="aasmConformanceFailed">—</b></div><div class="aasm-conformance-card"><span class="sub">Storage bypasses</span><b id="aasmConformanceBypasses">—</b></div></div><pre id="aasmConformanceDetail">Run a built-in driver to inspect the complete machine-readable report.</pre></section>
"""


_CONFORMANCE_SCRIPT = r"""
<script>
function aasmRenderConformance(value){const coverage=value.coverage||{};const audit=value.audit||{};$('aasmConformanceOverall').textContent=value.status||'—';$('aasmConformancePassed').textContent=String((coverage.passed||[]).length);$('aasmConformanceFailed').textContent=String((coverage.failed||[]).length);$('aasmConformanceBypasses').textContent=String(audit.total_violations||0);const cls=value.status==='PASS'?'good':(value.status==='FAIL'?'bad':'warn');$('aasmConformanceStatus').innerHTML=`<span class=${cls}>${esc(value.status||'UNKNOWN')}</span> · ${esc((value.adapter||{}).adapter_id||'adapter')} · ${esc(value.report_fingerprint||'')}`;$('aasmConformanceDetail').textContent=JSON.stringify(value,null,2)}
async function runAasmAdapterConformance(adapter){$('aasmConformanceStatus').textContent='Running conformance scenarios…';try{const value=await api('/v1/conformance/adapters/'+encodeURIComponent(adapter));aasmRenderConformance(value)}catch(error){$('aasmConformanceStatus').innerHTML=`<span class=bad>failed</span> · ${esc(error.message||error)}`}}
</script>
"""


def html_document() -> str:
    page = v29_html_document()
    page = page.replace("</style></head>", _CONFORMANCE_STYLE + "</style></head>", 1)
    page = page.replace('<div class="grid">', '<div class="grid">' + _CONFORMANCE_PANEL, 1)
    page = page.replace("</body>", _CONFORMANCE_SCRIPT + "</body>", 1)
    return page
