/* trading-agent — static site.
   Signal values are recomputed in the browser from raw claims rather than read
   from a precomputed number. That is what lets the leakage switch re-score the
   same evidence under either clock, which is the only honest way to *show*
   lookahead rather than assert it. The scoring mirrors signals/pipeline.py:score(). */

const SIGNALS = ["supply_risk", "price_pressure", "policy_shock"];
const LABEL = { supply_risk: "Supply risk", price_pressure: "Price pressure", policy_shock: "Policy shock" };
// Must mirror signals/pipeline.py:HALFLIFE_D exactly. A single global constant
// lived here after Python moved to per-signal decay, so the published site scored
// policy_shock with a 5-day half-life against the API's 45 and quietly disagreed
// with its own documentation.
const HALFLIFE_D = { supply_risk: 5.0, price_pressure: 2.0, policy_shock: 45.0 };
const BALANCE_SIGN = { tighter: 1, looser: -1, neutral: 0 };

let DATA = { claims: [], docs: [], meta: null };
let mermaidLib = null;

const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = (n, d = 1) => (n === null || n === undefined || Number.isNaN(n)) ? "—" : n.toFixed(d);

/* ------------------------------------------------------------------ scoring */

function score(claims, asOf) {
  const ref = asOf ? new Date(asOf) : new Date();
  const out = {};
  for (const sig of SIGNALS) {
    let num = 0, den = 0, n = 0;
    const hl = HALFLIFE_D[sig];
    for (const c of claims) {
      if (c.signal !== sig || c.injection_flag) continue;
      const ageD = (ref - new Date(c.event_time)) / 86400000;
      // A publisher-declared event_time in the future used to clamp to age 0, i.e.
      // maximum weight forever. Mirrors the guard in pipeline.py:score().
      if (ageD < -0.02) continue;
      const age = Math.max(ageD, 0);
      const w = Math.pow(0.5, age / hl) * (c.confidence || 0) * (c.novelty ?? 1);
      if (w <= 0) continue;
      const v = (c.magnitude || 0) * (sig === "price_pressure" ? (c.direction || 0) : 1);
      num += w * v; den += w; n++;
    }
    out[sig] = { value: den ? (num / den) * 100 : 0, claims: n, weight: den };
  }
  return out;
}

/* The switch. `ingest_time` is what we knew; `event_time` is what had happened.
   Scoring on the second is the single most common lookahead bug in the field. */
const visible = (asOf, clock) =>
  DATA.claims.filter(c => new Date(clock === "leaky" ? c.event_time : c.ingest_time) <= new Date(asOf));

/* ------------------------------------------------------------------ chrome */

function dateline() {
  const m = DATA.meta; if (!m) return;
  const d = s => s ? s.slice(0, 10) : "—";
  $("#dl-window").textContent = `window ${d(m.corpus.window_start)} → ${d(m.corpus.window_end)}`;
  $("#dl-corpus").textContent = `${m.corpus.documents} docs · ${m.corpus.clusters} clusters · ${m.corpus.claims} claims`;
  $("#dl-extractor").textContent = m.extractor;
}

function gauge(v, signed) {
  const pct = signed ? Math.min(Math.abs(v) / 100, 1) * 50 : Math.min(Math.max(v, 0) / 100, 1) * 100;
  const left = signed ? (v >= 0 ? 50 : 50 - pct) : 0;
  return `<div class="gauge">${signed ? '<i class="zero" style="left:50%"></i>' : ""}
    <i style="left:${left}%;width:${pct}%"></i></div>`;
}

function cards(sc) {
  return `<div class="signals">${SIGNALS.map(s => {
    const v = sc[s].value, signed = s === "price_pressure";
    const cls = sc[s].claims === 0 ? "nil" : (signed ? (v > 0 ? "pos" : v < 0 ? "neg" : "nil") : "");
    return `<div class="card">
      <div class="card-name">${LABEL[s]}</div>
      <div class="card-val ${cls}">${sc[s].claims ? (signed && v > 0 ? "+" : "") + fmt(v) : "—"}</div>
      ${gauge(v, signed)}
      <div class="card-foot"><span>${sc[s].claims} claims</span>
      <span>${signed ? "−100…+100" : "0…100"}</span></div>
    </div>`;
  }).join("")}</div>`;
}

/* ------------------------------------------------------------------ views */

function viewOverview() {
  const m = DATA.meta, c = m?.corpus || {};
  return `<div class="prose">
    <div class="kicker">Mintelligence assignment</div>
    <p class="lede">A design and a working slice for a system that reads the world's news,
    ships and fields, and turns them into commodity signals a research desk can act on —
    without inventing a single number.</p>

    <div class="stat-grid">
      <div class="stat"><b>${c.documents ?? "—"}</b><span>documents ingested</span></div>
      <div class="stat"><b>${c.clusters ?? "—"}</b><span>after dedup</span></div>
      <div class="stat"><b>${c.claims ?? "—"}</b><span>cited claims</span></div>
      <div class="stat"><b>0.4%</b><span>of cost is the LLM</span></div>
    </div>

    <h2>The finding that reframes the brief</h2>
    <p>The assignment says to ingest news from GDELT. We did, then measured what arrived.
    <b>Reuters, AP, Bloomberg, Cecafé, Conab and the ICO are at zero as identified sources</b>
    across 675,840 documents. But an earlier version of this page concluded from that that the
    signal was absent, and <b>that inference was wrong</b> — GDELT's own organizations field
    names Reuters in 1.66% of records and AP in 2.19%. The wire content is there; it arrives as
    syndicated republication, second-hand and stripped of attribution.</p>
    <p>Two further errors made the original claim look stronger than it was: substring matching
    manufactured two of its data points, and <b>two thirds of the corpus was never measured</b> —
    the translingual stream, which turns out to contain exactly the Vietnamese and Brazilian
    daily coffee price reporting the claim said was missing. The corrected finding is narrower
    and more useful: no primary source, no attribution, and a lexicon in the wrong alphabet.</p>

    <h2>Five things this argues</h2>

    <h3>Breadth, not depth, decides whether this works at all</h3>
    <p>Back out the information coefficient from the best published commodity-news result and you
    get <b>0.013</b>. Applied to one commodity that is a gross Sharpe around <b>0.1–0.3</b>, which
    is negative after realistic futures costs. More documents about coffee raise the precision of
    one forecast; they do not add bets. <b>Adding the twenty-first commodity is worth more than
    tripling coffee coverage</b> — so the marginal cost of commodity N+1 must be near zero, and
    nothing may be hardcoded to coffee.</p>

    <h3>The volumes in the brief are a misdirection</h3>
    <p>Ten million AIS pings a day is <b>116 messages a second</b> — one database, not a
    streaming cluster. Five hundred documents a day is about <b>nine dollars</b> of tokens.
    Only the imagery is genuinely large, and its cost is the licence, not the compute.
    Sizing this correctly is the first design decision, and most of the engineering
    budget belongs somewhere other than where the brief points.</p>

    <h3>Extraction is not prediction</h3>
    <p>The model turns prose into typed, cited claims. Ordinary arithmetic turns claims into
    signals. Fusing the two gives you a number nobody can audit, that isn't calibrated to
    any real probability, and that quietly inherits everything the model already knows about
    how the story ended.</p>

    <h3>Two clocks, from the first row</h3>
    <p>Every record stores when the world changed and when we learned about it. You can
    always recompute the first. You can never reconstruct the second after the fact — and
    without it, no backtest is honest. <a href="#/signals">The switch on the signals page</a>
    shows what the difference is worth.</p>

    <h3>Physical evidence is expensive to forge</h3>
    <p>Anyone can write an article. Nobody can repaint a warehouse roof or move two hundred
    thousand tonnes of coffee. Requiring text, vessel traffic and imagery to agree before a
    signal earns conviction is simultaneously the confidence model and the defence against
    planted news.</p>

    <h3>The document argues against itself where the evidence does</h3>
    <p>Three design decisions here are contradicted by the literature and are recorded as such
    rather than quietly dropped: novelty weighting is probably <i>backwards</i>, the futures basis
    probably subsumes the supply-risk signal, and the policy signal has too few events in a decade
    to ever be validated. One earlier claim — that pretraining contamination accounts for most of
    a news backtest's apparent alpha — <b>was simply wrong, and is retracted with the source
    quoted</b>. The mechanism that produced that error is the first entry in the failure-mode
    register.</p>

    <h2>What is actually running</h2>
    <p>The prototype ingests GDELT's bulk 15-minute knowledge-graph batches, collapses
    syndicated reprints, filters for trading relevance, and extracts claims with an LLM under
    a rule that every quote must appear verbatim in the source. It serves them over an API
    with a point-in-time replay parameter. Numbers on this site are from real runs —
    <a href="#/cost">including what it cost</a>.</p>
  </div>`;
}

/* Open on the instant where the two clocks disagree most. Defaulting to "now"
   showed a zero gap, which is true and useless -- at the end of the corpus both
   clocks have seen everything. The argument is only visible mid-replay. */
function widestGap(times) {
  let best = times[times.length - 1], bestN = -1;
  for (const t of times) {
    const n = visible(t, "leaky").length - visible(t, "honest").length;
    if (n > bestN) { bestN = n; best = t; }
  }
  return best;
}

function viewSignals() {
  const times = DATA.claims.flatMap(c => [c.ingest_time, c.event_time]).sort();
  const asOf = window.__asOf || (times.length ? widestGap(times) : new Date().toISOString());
  const clock = window.__clock || "honest";

  const honest = score(visible(asOf, "honest"), asOf);
  const leaky = score(visible(asOf, "leaky"), asOf);
  const shown = clock === "leaky" ? leaky : honest;
  const rows = visible(asOf, clock);

  const gap = SIGNALS.reduce((a, s) => a + Math.abs(leaky[s].value - honest[s].value), 0);
  const extra = visible(asOf, "leaky").length - visible(asOf, "honest").length;

  return `<div>
    ${cards(shown)}

    <div class="panel">
      <h3>The leakage switch</h3>
      <p class="panel-note">The same claims, scored under two clocks.
      <b>Ingest time</b> is what the desk actually knew at that instant.
      <b>Event time</b> is when the story happened — which includes reports that had not
      reached us yet. Scoring on the second is the most common lookahead bug in quantitative
      research, and it never looks like a bug: it looks like a better backtest.</p>
      <div class="switch">
        <button id="b-honest" aria-pressed="${clock === "honest"}">ingest_time · honest</button>
        <button id="b-leaky" class="danger" aria-pressed="${clock === "leaky"}">event_time · leaky</button>
        <span class="delta">${extra > 0
          ? `the leaky clock sees <b>${extra} claim${extra === 1 ? "" : "s"}</b> it could not have known · total signal shift <b>${fmt(gap)}</b> points`
          : `no gap at this instant — widen the replay below`}</span>
      </div>
      <div class="slider-row">
        <label for="asof">Replay as of — drag back through the corpus</label>
        <input id="asof" type="range" min="0" max="${Math.max(times.length - 1, 0)}"
               value="${Math.max(times.indexOf(asOf), 0)}">
        <output>${esc(asOf.slice(0, 16).replace("T", " "))}Z</output>
      </div>
    </div>

    <h2>Evidence ledger</h2>
    <p class="prose">Every number above decomposes into these rows, and every row carries the
    span it came from. A claim whose quote could not be found character-for-character in its
    source never reached this table.</p>
    <div class="tbl-wrap"><table>
      <thead><tr>
        <th>Signal</th><th class="num">Mag</th><th class="num">Conf</th>
        <th>Driver</th><th>Region</th><th>Evidence</th><th class="num">Known at</th>
      </tr></thead>
      <tbody>${rows.length ? rows.map(c => `<tr>
        <td><span class="tag ${c.signal}">${LABEL[c.signal]}</span></td>
        <td class="num">${c.direction ? (c.direction > 0 ? "+" : "−") : ""}${fmt(c.magnitude, 2)}</td>
        <td class="num">${fmt(c.confidence, 2)}</td>
        <td>${esc(c.driver)}</td>
        <td>${esc(c.region)}</td>
        <td><blockquote class="ev">${esc(c.evidence_quote)}</blockquote>
            <span class="src">${c.source_url
              ? `<a href="${esc(c.source_url)}" rel="noopener noreferrer" target="_blank">${esc(c.domain || "source")}</a> — ${esc(c.source_title || "")}`
              : ""}</span></td>
        <td class="num">${esc(c.ingest_time.slice(5, 16).replace("T", " "))}</td>
      </tr>`).join("") : `<tr><td colspan="7" class="loading">No claims visible at this instant.</td></tr>`}
      </tbody>
    </table></div>
  </div>`;
}

function bindSignals() {
  const times = DATA.claims.flatMap(c => [c.ingest_time, c.event_time]).sort();
  const set = (k, v) => { window[k] = v; window.__inPlace = true; render(); };
  $("#b-honest")?.addEventListener("click", () => set("__clock", "honest"));
  $("#b-leaky")?.addEventListener("click", () => set("__clock", "leaky"));
  $("#asof")?.addEventListener("input", e => set("__asOf", times[+e.target.value]));
}

/* ------------------------------------------------------------------ cost */

const COST = {
  aois: { label: "Satellite AOIs monitored", min: 50, max: 1000, step: 50, val: 200 },
  km2: { label: "km² per AOI", min: 1, max: 25, step: 1, val: 4 },
  usdkm2: { label: "Commercial tasking $/km²", min: 5, max: 25, step: 1, val: 10 },
  trigger: { label: "Tasking events per month (0 = daily blanket)", min: 0, max: 120, step: 5, val: 30 },
  docs: { label: "Text items per day", min: 500, max: 500000, step: 500, val: 200000 },
  cascade: { label: "% routed to the cheap model", min: 0, max: 99, step: 1, val: 95 },
  tb: { label: "Imagery TB per day", min: 1, max: 5, step: 1, val: 1 },
  tier: { label: "% of storage tiered to archive", min: 0, max: 95, step: 5, val: 90 },
};

function costModel(v) {
  const daily = v.aois * v.km2;
  const tasking = v.trigger === 0 ? daily * v.usdkm2 * 30 : v.trigger * 20 * v.usdkm2;
  const tok = v.docs * 200 / 1e6 * 30;
  const llm = tok * ((1 - v.cascade / 100) * 3 + (v.cascade / 100) * 0.10);
  const tb = v.tb * 365;
  const store = (tb * 1000) * ((1 - v.tier / 100) * 0.023 + (v.tier / 100) * 0.004);
  const fixed = { People: 30000, "AIS licence": 20000, "Exchange + derived data": 12000, "Cloud infra": 4000, GPU: 700, ASR: 60 };
  const lines = { ...fixed, "Satellite tasking": tasking, "Object storage": store, "LLM tokens": llm };
  const total = Object.values(lines).reduce((a, b) => a + b, 0);
  return { lines, total };
}

function viewCost() {
  const v = Object.fromEntries(Object.entries(COST).map(([k, c]) => [k, window.__cost?.[k] ?? c.val]));
  const { lines, total } = costModel(v);
  const naive = costModel({ ...v, trigger: 0, cascade: 0, tier: 0 });
  const usd = n => n >= 1000 ? "$" + Math.round(n).toLocaleString() : "$" + n.toFixed(0);
  const sorted = Object.entries(lines).sort((a, b) => b[1] - a[1]);

  return `<div>
    <div class="prose">
      <div class="kicker">Deliverable 4</div>
      <p class="lede">The counter-intuitive result: the LLM is the cheapest part of the LLM
      system. Data licences are about half the bill, people are most of the rest, and
      satellite tasking policy alone accounts for almost all of the difference between a
      workable month and a ruinous one.</p>
    </div>

    <div class="stat-grid">
      <div class="stat"><b>${usd(total)}</b><span>per month · staged</span></div>
      <div class="stat"><b>${usd(naive.total)}</b><span>per month · naive</span></div>
      <div class="stat"><b>${(naive.total / total).toFixed(0)}×</b><span>difference</span></div>
      <div class="stat"><b>${(100 * lines["LLM tokens"] / total).toFixed(1)}%</b><span>is LLM tokens</span></div>
    </div>

    <div class="panel">
      <h3>Assumptions — drag them</h3>
      <p class="panel-note">Setting tasking events to zero means daily blanket commercial
      tasking. Setting the cascade to zero sends every item to a frontier model. Those two
      alone account for most of the gap.</p>
      ${Object.entries(COST).map(([k, c]) => `<div class="slider-row">
        <label for="c-${k}">${c.label}</label>
        <input id="c-${k}" type="range" min="${c.min}" max="${c.max}" step="${c.step}" value="${v[k]}">
        <output>${v[k].toLocaleString()}</output>
      </div>`).join("")}
    </div>

    <div class="tbl-wrap"><table>
      <thead><tr><th>Line</th><th class="num">$ / month</th><th class="num">Share</th><th>&nbsp;</th></tr></thead>
      <tbody>${sorted.map(([k, n]) => `<tr>
        <td>${k}</td><td class="num">${usd(n)}</td>
        <td class="num">${(100 * n / total).toFixed(1)}%</td>
        <td style="width:34%"><div class="gauge"><i style="left:0;width:${(100 * n / sorted[0][1]).toFixed(1)}%"></i></div></td>
      </tr>`).join("")}
      <tr><td><b>Total</b></td><td class="num"><b>${usd(total)}</b></td><td class="num">100%</td><td></td></tr>
      </tbody>
    </table></div>
    <div class="prose"><p>Full workings, excluded costs and what the prototype actually
    metered are in <a href="#/cost-doc">the cost document</a>.</p></div>
  </div>`;
}

function bindCost() {
  Object.keys(COST).forEach(k => $("#c-" + k)?.addEventListener("input", e => {
    window.__cost = { ...(window.__cost || {}), [k]: +e.target.value };
    window.__inPlace = true;
    render();
  }));
}

/* ------------------------------------------------------------------ docs */

async function viewDoc(file) {
  const md = await fetch(`docs/${file}`).then(r => r.ok ? r.text() : `# Not found\n\n\`${file}\``);
  const blocks = [];
  const src = md.replace(/```mermaid\n([\s\S]*?)```/g, (_, code) => {
    blocks.push(code); return `<div class="mermaid" data-i="${blocks.length - 1}"></div>`;
  });
  setTimeout(() => drawMermaid(blocks), 0);
  return `<div class="doc prose">${marked.parse(src)}</div>`;
}

async function drawMermaid(blocks) {
  const nodes = document.querySelectorAll(".mermaid[data-i]");
  if (!nodes.length) return;
  if (!mermaidLib) {
    try {
      mermaidLib = (await import("https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs")).default;
      // theme:"base" with no explicit lineColor draws edges in a tint that is
      // invisible on cream paper -- the nodes render and the arrows silently do not.
      mermaidLib.initialize({
        startOnLoad: false, theme: "base", securityLevel: "loose",
        flowchart: { curve: "basis", nodeSpacing: 44, rankSpacing: 60, useMaxWidth: true },
        themeVariables: {
          background: "transparent",
          primaryColor: "#3B4252", primaryTextColor: "#ECEFF4", primaryBorderColor: "#81A1C1",
          secondaryColor: "#4C566A", tertiaryColor: "#2E3440",
          lineColor: "#6B6355", textColor: "#16130E",
          edgeLabelBackground: "transparent",
          fontFamily: "JetBrains Mono, monospace", fontSize: "13px",
        },
      });
    } catch { nodes.forEach(n => n.textContent = blocks[+n.dataset.i]); return; }
  }
  for (const n of nodes) {
    try {
      const { svg } = await mermaidLib.render("m" + Math.random().toString(36).slice(2), blocks[+n.dataset.i]);
      n.innerHTML = svg;
      // Arrowheads live in <defs> and ignore the lineColor theme variable, so the
      // edge is coloured but its head is not. Patch them directly.
      n.querySelectorAll("marker path, marker polygon").forEach(m => {
        m.setAttribute("fill", "#6B6355"); m.setAttribute("stroke", "#6B6355");
      });
      n.querySelectorAll("path.flowchart-link, .edgePath path, .relation").forEach(e => {
        if (!e.getAttribute("stroke") || e.getAttribute("stroke") === "none")
          e.setAttribute("stroke", "#6B6355");
        e.setAttribute("stroke-width", "1.6");
      });
    } catch { n.innerHTML = `<pre>${esc(blocks[+n.dataset.i])}</pre>`; }
  }
}

/* ------------------------------------------------------------------ router */

const ROUTES = {
  "#/": { render: viewOverview, surface: "paper" },
  "#/signals": { render: viewSignals, bind: bindSignals, surface: "ink" },
  "#/architecture": { doc: "ARCHITECTURE.md", surface: "paper" },
  "#/failure-modes": { doc: "FAILURE_MODES.md", surface: "paper" },
  "#/cost": { render: viewCost, bind: bindCost, surface: "paper" },
  "#/cost-doc": { doc: "COST.md", surface: "paper" },
  "#/case": { doc: "CASE_STUDY.md", surface: "paper" },
  "#/orchestration": { doc: "ORCHESTRATION.md", surface: "paper" },
  "#/sources": { doc: "SOURCES.md", surface: "paper" },
  "#/measurements": { doc: "MEASUREMENTS.md", surface: "paper" },
  "#/wheat": { doc: "WHEAT.md", surface: "paper" },
  "#/edge": { doc: "EDGE.md", surface: "paper" },
  "#/pipeline": { doc: "PIPELINE.md", surface: "paper" },
  "#/learning": { doc: "LEARNING.md", surface: "paper" },
};

async function render() {
  const hash = location.hash || "#/";
  const r = ROUTES[hash] || ROUTES["#/"];
  document.documentElement.dataset.surface = r.surface;
  document.querySelectorAll("nav.tabs a").forEach(a =>
    a.toggleAttribute("aria-current", a.getAttribute("href") === hash));
  const view = $("#view");
  const keepScroll = window.__inPlace;
  const y = window.scrollY;
  view.innerHTML = r.doc ? await viewDoc(r.doc) : r.render();
  r.bind?.();
  // Only reset scroll on an actual route change. Re-rendering in place (dragging a
  // slider, flipping the leakage switch) used to replace the DOM node under the
  // cursor AND jump to the top, so the interactive arguments could not be dragged.
  if (keepScroll) { window.scrollTo(0, y); window.__inPlace = false; }
  else window.scrollTo(0, 0);
}

async function boot() {
  try {
    const [claims, docs, meta] = await Promise.all(
      ["claims", "docs", "meta"].map(f => fetch(`data/${f}.json`).then(r => r.json())));
    DATA = { claims, docs, meta };
  } catch {
    $("#view").innerHTML = `<p class="loading">Signal data not generated yet — run <code>make export</code>.</p>`;
  }
  dateline();
  window.addEventListener("hashchange", () => { window.__scrolled = false; render(); });
  render();
}

boot();
