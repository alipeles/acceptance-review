"""Merge the extracted sample and the judgements into one labeling page."""
import json, sys, html
from pathlib import Path

here = Path(__file__).parent
extract = json.load(open(here / sys.argv[1]))
judge = json.load(open(here / sys.argv[2]))
out = here / sys.argv[3]

MAX_HUNK = 90

def trim(content):
    if not content:
        return None
    lines = content.splitlines()
    if len(lines) <= MAX_HUNK:
        return content
    return "\n".join(lines[:MAX_HUNK]) + f"\n… ({len(lines) - MAX_HUNK} more lines)"

items = []
for it in extract["items"]:
    j = judge["items"].get(it["id"], {})
    defects = []
    for d in it.get("defects", []):
        jd = (j.get("defects") or {}).get(d["id"], {})
        mut = d["mutation"][0] if d.get("mutation") else None
        defects.append({
            "id": d["id"].split("/", 1)[1], "type": d["type"], "description": d["description"],
            "mutant": (mut or {}).get("outcome"),
            "mutant_reason": ((mut or {}).get("reason") or "")[:260],
            "killed_by": [t.split("::")[-1] for t in (mut or {}).get("killing_tests", [])][:3],
            "call": jd.get("call"), "note": jd.get("note"),
        })
    items.append({
        "id": it["id"], "kind": it["kind"], "ordinal": it["ordinal"],
        "description": it["description"], "observable": it.get("observable_behavior"),
        "type": it.get("type"), "importance": it.get("importance"), "explicit": it.get("explicit"),
        "severity": it.get("severity"),
        "spans": it.get("source_spans") or [],
        "coverage_status": it.get("coverage_status"), "evidence_class": it.get("evidence_class"),
        "covered": it.get("covered_defects"), "enumerated": it.get("enumerated_defects"),
        "code": [{"path": c["path"], "header": c["header"], "content": trim(c["content"])} for c in it["code"]],
        "tests": [{"id": t["id"], "source": t["source"]} for t in it.get("tests", [])],
        "defects": defects,
        "recommendations": [{"defect": r["plausible_defect"], "inputs": r["required_inputs"],
                             "assertions": r.get("required_assertions", [])} for r in it.get("recommendations", [])],
        "judgement": {k: j.get(k) for k in ("plain", "label", "causes", "explanation", "agent")},
    })

data = {
    "meta": {"repo": extract["repo"], "revision": extract["reviewed_revision"][:7], "verdict": extract["verdict"],
             "rationale": extract["rationale"], "obligation_count": extract["obligation_count"]},
    "task_text": extract["task_text"],
    "labels": judge["labels"], "causes": judge["causes"], "context": judge["context"],
    "items": items,
}

page = r"""<title>Materiality Sample 1</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=Source+Sans+3:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: a review desk. Sticky item rail on the left, one dossier per finding on the right; phone collapses the rail to a scrolling strip. */
:root{
  --bg:#f3f4f1; --paper:#ffffff; --ink:#1d2320; --muted:#5d665f; --line:#d5d9d2; --accent:#1f6f6b; --accent-ink:#ffffff;
  --code-bg:#eef0ec; --quote:#e9eee7;
  --material:#a63d2a; --immaterial:#9a6a12; --wrong:#3a5a8c;
  --ok:#2e7d4f; --warn:#b06b00;
  --serif:"Source Serif 4",Georgia,serif; --sans:"Source Sans 3",system-ui,sans-serif; --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#171a18; --paper:#1f2320; --ink:#e7eae4; --muted:#a2aba3; --line:#343a35; --accent:#5fb8b2; --accent-ink:#0f1a19;
  --code-bg:#151816; --quote:#262c28; --material:#e07a63; --immaterial:#d6a24a; --wrong:#8fb0e0; --ok:#6cc38f; --warn:#e0a24a; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#171a18; --paper:#1f2320; --ink:#e7eae4; --muted:#a2aba3; --line:#343a35; --accent:#5fb8b2; --accent-ink:#0f1a19;
  --code-bg:#151816; --quote:#262c28; --material:#e07a63; --immaterial:#d6a24a; --wrong:#8fb0e0; --ok:#6cc38f; --warn:#e0a24a; color-scheme:dark}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:16px;line-height:1.5;margin:0}
.wrap{max-width:1200px;margin:0 auto;padding-block:24px 80px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
h1,h2,h3{font-family:var(--serif);font-weight:600;text-wrap:balance;margin:0}
h1{font-size:2rem;line-height:1.15}
h2{font-size:1.35rem}
h3{font-size:1.05rem}
p{margin:0}
.lede{color:var(--muted);max-width:68ch;margin-top:6px}
.grid{display:grid;grid-template-columns:260px minmax(0,1fr);gap:28px;margin-top:28px}
@media (max-width:860px){.grid{grid-template-columns:minmax(0,1fr)}}
nav.rail{position:sticky;top:env(safe-area-inset-top,0px);align-self:start;max-height:calc(100vh - 24px);overflow:auto;padding-right:4px}
@media (max-width:860px){nav.rail{position:static;max-height:none;display:flex;gap:6px;overflow-x:auto;padding-bottom:8px}}
.rail a{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;color:var(--ink);text-decoration:none;font-size:.9rem;white-space:nowrap}
.rail a:hover{background:var(--quote)}
.rail .dot{width:9px;height:9px;border-radius:50%;border:1.5px solid var(--muted);flex:none}
.rail .dot.done{background:var(--ok);border-color:var(--ok)}
.rail .num{font-family:var(--mono);font-size:.78rem;color:var(--muted);width:2.2em;flex:none}
.rail .sect{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:12px 8px 4px}
@media (max-width:860px){.rail .sect{display:none}.rail a{border:1px solid var(--line);background:var(--paper)}}
.progress{font-size:.85rem;color:var(--muted);padding:6px 8px 10px;font-variant-numeric:tabular-nums}
main{min-width:0;display:flex;flex-direction:column;gap:24px}
.panel{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:22px}
.panel + .panel{margin-top:0}
.intro h2{margin-bottom:8px}
.intro p + p{margin-top:10px}
.intro .defs{display:grid;gap:10px;margin-top:14px}
.def{display:grid;grid-template-columns:auto 1fr;gap:12px;align-items:start}
details.task{margin-top:14px}
details.task summary{cursor:pointer;color:var(--accent);font-weight:600}
pre.task{white-space:pre-wrap;font-family:var(--mono);font-size:.82rem;line-height:1.5;background:var(--code-bg);padding:14px;border-radius:6px;margin-top:10px;overflow-x:auto}
article.item{scroll-margin-top:12px}
.item header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 14px;margin-bottom:6px}
.item .ord{font-family:var(--mono);font-size:.85rem;color:var(--muted)}
.item .kind{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.pills{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.pill{font-family:var(--mono);font-size:.74rem;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);background:var(--bg)}
.pill.strong{border-color:var(--accent);color:var(--accent)}
.span{margin-top:12px;background:var(--quote);border-left:3px solid var(--accent);padding:10px 14px;border-radius:0 6px 6px 0}
.span .k{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:2px}
.span q{font-family:var(--serif);font-size:1.02rem;quotes:"“" "”"}
.plain{margin-top:14px;max-width:70ch}
.sec{margin-top:18px}
.sec > summary{cursor:pointer;font-weight:600;color:var(--accent);list-style:none;display:flex;gap:8px;align-items:center}
.sec > summary::before{content:"▸";font-size:.8rem;transition:transform .15s}
.sec[open] > summary::before{transform:rotate(90deg)}
.sec > summary .n{color:var(--muted);font-weight:400;font-size:.9rem}
.sec .body{margin-top:10px;display:flex;flex-direction:column;gap:12px}
pre.code{margin:0;font-family:var(--mono);font-size:.78rem;line-height:1.45;background:var(--code-bg);padding:12px;border-radius:6px;overflow-x:auto;white-space:pre}
.file{font-family:var(--mono);font-size:.78rem;color:var(--muted);margin-bottom:4px}
table.defects{width:100%;border-collapse:collapse;font-size:.9rem}
table.defects th,table.defects td{text-align:left;vertical-align:top;padding:8px 8px;border-top:1px solid var(--line)}
table.defects th{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);border-top:0}
table.defects td:first-child{min-width:280px;width:50%}
table.defects td.c{min-width:150px;overflow-wrap:anywhere}
.twrap{overflow-x:auto}
.call{font-family:var(--mono);font-size:.74rem;padding:1px 7px;border-radius:999px;border:1px solid currentColor}
.call.probable{color:var(--material)} .call.possible{color:var(--immaterial)} .call.not-a-defect{color:var(--wrong)}
.mut{font-family:var(--mono);font-size:.74rem;color:var(--muted)}
.mut.killed{color:var(--ok)} .mut.survived{color:var(--warn)}
.rec{background:var(--quote);padding:10px 14px;border-radius:6px;font-size:.92rem}
.rec b{font-weight:600}
.judge{margin-top:18px;border:1px solid var(--line);border-radius:8px;padding:16px;display:grid;gap:10px}
.judge .row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.lab{font-family:var(--mono);font-size:.8rem;font-weight:500;padding:3px 10px;border-radius:999px;color:#fff}
.lab.material{background:var(--material)} .lab.immaterial{background:var(--immaterial)} .lab.wrong{background:var(--wrong)}
:root[data-theme="dark"] .lab,:root:not([data-theme="light"]) .lab{color:var(--paper)}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]) .lab{color:#fff}}
:root[data-theme="light"] .lab{color:#fff}
.cause{font-size:.8rem;color:var(--muted);border:1px dashed var(--line);padding:1px 8px;border-radius:999px}
.agent{font-size:.88rem;color:var(--muted)}
.agent b{color:var(--ink);font-weight:600}
.you{margin-top:14px;border-top:1px solid var(--line);padding-top:14px;display:grid;gap:10px}
.you .k{font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.btns{display:flex;flex-wrap:wrap;gap:8px}
button{font:inherit;cursor:pointer;border-radius:6px;border:1px solid var(--line);background:var(--paper);color:var(--ink);padding:7px 14px}
button:hover{border-color:var(--accent)}
button:focus-visible,textarea:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
button.on{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.radios{display:flex;flex-wrap:wrap;gap:12px;font-size:.92rem}
.radios label{display:flex;gap:6px;align-items:center;cursor:pointer}
textarea{font:inherit;font-size:.92rem;width:100%;min-height:64px;border:1px solid var(--line);border-radius:6px;padding:8px;background:var(--paper);color:var(--ink);resize:vertical}
.status{font-size:.82rem;color:var(--muted);min-height:1.2em}
.status.saved{color:var(--ok)}
.banner{font-size:.88rem;background:var(--quote);border-radius:6px;padding:10px 14px}
.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:14px}
.tile{border:1px solid var(--line);border-radius:6px;padding:10px 12px}
.tile .v{font-family:var(--serif);font-size:1.6rem;line-height:1.1;font-variant-numeric:tabular-nums}
.tile .l{font-size:.78rem;color:var(--muted)}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="wrap">
  <h1>Materiality Sample 1</h1>
  <p class="lede">Twenty findings from one review of the job-search CRM (issue #5, usage telemetry). Each comes with the context to judge it and a proposed label. Your job is to agree or override, and say why when you override.</p>

  <div class="grid">
    <nav class="rail" id="rail"></nav>
    <main id="main"></main>
  </div>
</div>

<script id="data" type="application/json">__DATA__</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const state = {};   // id -> {agree, label, note}
let db = null, saveMode = 'none';

function ratingPills(it){
  const p = [];
  if (it.kind === 'obligation'){
    p.push(`<span class="pill">${esc(it.type)}</span>`);
    p.push(`<span class="pill">importance: ${esc(it.importance)}</span>`);
    p.push(`<span class="pill">${it.explicit ? 'explicit' : 'inferred'}</span>`);
    p.push(`<span class="pill strong">code: ${esc(it.coverage_status ?? '—')}</span>`);
    p.push(`<span class="pill strong">tests: ${esc(it.evidence_class ?? 'not rated')}${it.enumerated ? ` (${it.covered} of ${it.enumerated} defects covered)` : ''}</span>`);
  } else {
    p.push(`<span class="pill strong">severity: ${esc(it.severity)}</span>`);
  }
  return `<div class="pills">${p.join('')}</div>`;
}

function defectsTable(it){
  if (!it.defects.length) return '';
  const rows = it.defects.map(d => `<tr>
    <td><div style="font-family:var(--mono);font-size:.78rem;color:var(--muted)">${esc(d.id)} <span class="pill">${esc(d.type)}</span></div><div>${esc(d.description)}</div></td>
    <td class="c"><span class="mut ${esc(d.mutant)}">${esc(d.mutant ?? '—')}</span>${d.killed_by.length ? `<div class="mut">by ${esc(d.killed_by.join(', '))}</div>` : ''}</td>
    <td><span class="call ${esc(d.call)}">${esc(d.call ?? '—')}</span><div style="font-size:.85rem;margin-top:4px">${esc(d.note ?? '')}</div></td>
  </tr>`).join('');
  return `<details class="sec" open><summary>Failure modes the tool enumerated <span class="n">(${it.defects.length})</span></summary><div class="body"><div class="twrap"><table class="defects">
    <thead><tr><th>Defect</th><th>Mutant</th><th>Proposed call</th></tr></thead><tbody>${rows}</tbody></table></div>
    <p style="font-size:.82rem;color:var(--muted)">Mutant: the tool injected this bug and ran the suite. <i>killed</i> means a test failed, <i>survived</i> means none did, <i>already_present</i> means the code already looks like the described defect, <i>no_usable_edit</i> means it could not construct the bug. Proposed call: <i>probable</i> is a failure mode of this requirement worth a test; <i>possible</i> could happen but a project would not insist; <i>not-a-defect</i> is contradicted by the task, the code, or a recorded decision.</p>
  </div></details>`;
}

function card(it){
  const j = it.judgement;
  const n = it.kind === 'obligation' ? `Obligation ${it.ordinal} of ${D.meta.obligation_count}` : `Unrequested change ${it.ordinal}`;
  const spans = it.spans.length ? `<div class="span"><span class="k">From the task</span>${it.spans.map(s => `<q>${esc(s.replace(/\s+/g,' '))}</q>`).join('<br>')}</div>` : '';
  const code = it.code.filter(c => c.content).map(c => `<div><div class="file">${esc(c.path)} <span style="opacity:.7">${esc(c.header)}</span></div><pre class="code">${esc(c.content)}</pre></div>`).join('');
  const tests = it.tests.map(t => `<div><div class="file">${esc(t.id)}</div>${t.source ? `<pre class="code">${esc(t.source)}</pre>` : '<p class="agent">source not found</p>'}</div>`).join('');
  const recs = it.recommendations.map(r => `<div class="rec"><b>Would detect:</b> ${esc(r.defect)}<br><b>Inputs:</b> ${esc(r.inputs)}</div>`).join('');
  const causes = (j.causes || []).map(c => `<span class="cause" title="${esc(D.causes[c] || '')}">${esc(D.causes[c] || c)}</span>`).join('');
  return `<article class="item panel" id="${esc(it.id)}">
    <header><span class="ord">${n}</span><span class="kind">${it.kind === 'obligation' ? 'obligation' : 'unrequested change'}</span></header>
    <h2>${esc(it.description)}</h2>
    ${it.observable ? `<p class="agent" style="margin-top:4px">Observable behavior, as the tool phrased it: ${esc(it.observable)}</p>` : ''}
    ${ratingPills(it)}
    ${spans}
    <p class="plain">${esc(j.plain)}</p>
    ${it.tests.length ? `<details class="sec"><summary>Tests the tool mapped to this <span class="n">(${it.tests.length})</span></summary><div class="body">${tests}</div></details>` : `<p class="agent" style="margin-top:14px">The tool mapped no tests to this.</p>`}
    ${defectsTable(it)}
    ${recs ? `<details class="sec"><summary>Tests the tool recommended <span class="n">(${it.recommendations.length})</span></summary><div class="body">${recs}</div></details>` : ''}
    ${code ? `<details class="sec"><summary>Code the tool pointed at <span class="n">(${it.code.filter(c=>c.content).length} hunks)</span></summary><div class="body">${code}</div></details>` : ''}
    <div class="judge">
      <div class="row"><span class="k" style="font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)">Proposed label</span><span class="lab ${esc(j.label)}">${esc(j.label)}</span>${causes}</div>
      <p>${esc(j.explanation)}</p>
      <p class="agent"><b>Coding agent's own triage:</b> ${esc(j.agent)}</p>
      <div class="you">
        <span class="k">Your call</span>
        <div class="btns"><button type="button" id="agree-${esc(it.id)}" data-id="${esc(it.id)}" data-v="agree">Agree</button><button type="button" id="disagree-${esc(it.id)}" data-id="${esc(it.id)}" data-v="disagree">Disagree</button><button type="button" id="unsure-${esc(it.id)}" data-id="${esc(it.id)}" data-v="unsure">Not sure</button></div>
        <div class="radios" id="radios-${esc(it.id)}" hidden>
          ${['material','immaterial','wrong'].map(l => `<label><input type="radio" name="label-${esc(it.id)}" id="label-${esc(it.id)}-${l}" value="${l}"> ${l}</label>`).join('')}
        </div>
        <textarea id="note-${esc(it.id)}" placeholder="Why, in a sentence. Especially useful when you disagree or aren't sure."></textarea>
        <div class="status" id="status-${esc(it.id)}"></div>
      </div>
    </div>
  </article>`;
}

function intro(){
  const defs = Object.entries(D.labels).map(([k,v]) => `<div class="def"><span class="lab ${k}">${k}</span><span>${esc(v)}</span></div>`).join('');
  return `<section class="panel intro">
    <h2>What you are looking at</h2>
    <p>${esc(D.context.feature)}</p>
    <p>${esc(D.context.run)}</p>
    <p class="agent">${esc(D.context.agent_caveat)}</p>
    <h3 style="margin-top:16px">The question for each finding</h3>
    <p>Would a reasonable project have blocked the merge on this? Three answers:</p>
    <div class="defs">${defs}</div>
    <p style="margin-top:12px">The split between <i>immaterial</i> and <i>wrong</i> matters because they get fixed differently: wrong findings are an accuracy problem in a prompt or a mapping step; immaterial ones are the calibration question you raised. If you find yourself unsure which side a finding falls on, say so in the note. That boundary is the thing this sample is meant to locate.</p>
    <details class="task"><summary>The full task file the agent was given</summary><pre class="task">${esc(D.task_text)}</pre></details>
    <div class="summary" id="summary"></div>
    <div class="banner" id="savebanner" style="margin-top:12px"></div>
  </section>`;
}

function rail(){
  const obl = D.items.filter(i => i.kind === 'obligation'), unr = D.items.filter(i => i.kind !== 'obligation');
  const link = i => `<a href="#${esc(i.id)}"><span class="dot" id="dot-${esc(i.id)}"></span><span class="num">${i.kind==='obligation' ? i.ordinal : 'U'+i.ordinal}</span><span style="overflow:hidden;text-overflow:ellipsis">${esc(i.id)}</span></a>`;
  return `<div class="progress" id="progress"></div><div class="sect">Obligations</div>${obl.map(link).join('')}<div class="sect">Unrequested changes</div>${unr.map(link).join('')}`;
}

function render(){
  document.getElementById('rail').innerHTML = rail();
  document.getElementById('main').innerHTML = intro() + D.items.map(card).join('');
  document.querySelectorAll('.btns button').forEach(b => b.addEventListener('click', () => choose(b.dataset.id, b.dataset.v)));
  D.items.forEach(it => {
    document.getElementById(`radios-${it.id}`).addEventListener('change', e => { setState(it.id, {label: e.target.value}); });
    const ta = document.getElementById(`note-${it.id}`);
    let t; ta.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => setState(it.id, {note: ta.value}), 600); });
  });
  paintAll();
}

function choose(id, v){
  const it = D.items.find(i => i.id === id);
  const patch = {agree: v};
  if (v === 'agree') patch.label = it.judgement.label;
  setState(id, patch);
}

async function setState(id, patch){
  state[id] = Object.assign({}, state[id] || {}, patch, {at: new Date().toISOString(), proposed: D.items.find(i=>i.id===id).judgement.label});
  paint(id);
  const st = document.getElementById(`status-${id}`);
  st.className = 'status'; st.textContent = 'Saving…';
  try {
    if (db) { await db.collection('labels').doc(id).set(state[id]); }
    else { localStorage.setItem('mat1:' + id, JSON.stringify(state[id])); }
    st.className = 'status saved'; st.textContent = db ? 'Saved' : 'Saved in this browser only';
  } catch (e) { st.textContent = 'Could not save: ' + (e && e.code || e); }
}

function paint(id){
  const s = state[id] || {};
  ['agree','disagree','unsure'].forEach(v => document.getElementById(`${v}-${id}`).classList.toggle('on', s.agree === v));
  const radios = document.getElementById(`radios-${id}`);
  radios.hidden = !(s.agree === 'disagree' || s.agree === 'unsure');
  if (s.label) { const r = document.getElementById(`label-${id}-${s.label}`); if (r) r.checked = true; }
  const ta = document.getElementById(`note-${id}`);
  if (s.note !== undefined && document.activeElement !== ta) ta.value = s.note;
  document.getElementById(`dot-${id}`).classList.toggle('done', !!s.agree);
  summary();
}
function paintAll(){ D.items.forEach(i => paint(i.id)); }

function summary(){
  const done = D.items.filter(i => state[i.id] && state[i.id].agree);
  document.getElementById('progress').textContent = `${done.length} of ${D.items.length} labeled`;
  const count = k => done.filter(i => (state[i.id].label || '') === k).length;
  const agree = done.filter(i => state[i.id].agree === 'agree').length;
  const dis = done.filter(i => state[i.id].agree === 'disagree').length;
  document.getElementById('summary').innerHTML = [
    ['Labeled', `${done.length}/${D.items.length}`], ['Agreed', agree], ['Overridden', dis],
    ['Material', count('material')], ['Immaterial', count('immaterial')], ['Wrong', count('wrong')],
  ].map(([l,v]) => `<div class="tile"><div class="v">${v}</div><div class="l">${l}</div></div>`).join('');
}

render();

(async () => {
  const banner = document.getElementById('savebanner');
  try { db = await window.claude?.use?.('db'); } catch (e) { db = null; }
  if (db) {
    banner.textContent = 'Your labels save as you go and I can read them back from here.';
    db.collection('labels').onSnapshot(snap => {
      snap.docs.forEach(d => { if (d.exists) { state[d.id] = d.data(); } });
      paintAll();
    }, err => { banner.textContent = 'Live sync stopped (' + err.code + '); labels you set now still save.'; });
  } else {
    banner.textContent = 'Shared saving is not available in this view, so labels are kept in this browser only. Tell me when you are done and I will ask for them.';
    try { D.items.forEach(i => { const v = localStorage.getItem('mat1:' + i.id); if (v) state[i.id] = JSON.parse(v); }); } catch (e) {}
    paintAll();
  }
})();
</script>
"""
out.write_text(page.replace("__DATA__", json.dumps(data).replace("</", "<\\/")))
print(out, out.stat().st_size, "bytes")
