# Is a text pipeline capable of edge at all?

The brief asks for a system that extracts trading signals from news and reports. This document
asks the prior question the brief takes for granted — *can that work?* — and redesigns around the
answer.

The short version: **as specified, no. Reframed, yes, and narrowly.** Reading news faster than the
market is not a strategy. Maintaining a continuously-updated estimate of a physical quantity the
market can only see monthly is.

---

## 1. What this project already proved, against its own interest

Every attractive claim generated during this build died under measurement. That record is the
most useful input to the redesign, so it is stated first:

| Claim | Fate |
|---|---|
| Certified stocks predict price | r = **+0.002** |
| Gas → urea → coffee cost chain | r ≈ 0, and the cause peaked **six months after** the effect |
| Fertiliser costs cut yields | falsified by a **record crop (+12.8%)** |
| Positioning crowding causes squeezes | correlation real (t = +2.79), **mechanism wrong** — quiet shorts, not squeezed longs |
| GDELT lacks wire coverage | it has it; only **31%** of the corpus had been measured |
| The ICE rule was buried | **Reuters had it the next day** |
| Batch sizes ~1,550/day | actually **1,004**; the whole funnel was 5x inflated |
| The pipeline is 97% commodity-agnostic | **survivorship** — it counted code that exists, not code that is missing |

Not one was a coding error. Each was a plausible story that survived because nothing in the
process was built to kill it. **The design's first obligation is therefore falsifiability, not
capability.**

And the single consistent finding across the two cases that *did* survive — Colombian rust, and
India's FCI procurement shortfall — is that **the edge was never detection.** Reuters reported
the ICE rule the day after it was announced. India's procurement numbers were public and in the
press before the export ban. In both cases the fact was available and the market still moved
later, which means the binding constraint was not information *acquisition*.

---

## 2. The four positions where text can pay

There are only four, and "reading articles faster" is not among them.

**1. Upstream of the wire.** Consume the mandatory-disclosure feeds the journalist reads *in order
to write* the article. You are not racing Reuters; you are reading Reuters' source. Latency edge
measured in minutes to hours, and it decays as others do the same.

**2. Below the attention threshold.** No journalist writes "one 40 MW unit in Hungary is out for
three days." Fifty simultaneous such facts are a market event with no name and no story. **This
is not a race** — it cannot be arbitraged by being faster, only by having assembled the corpus.
Structurally the most durable of the four.

**3. Across a language or jurisdiction boundary.** Published in Portuguese on a ministry site with
no English coverage for hours or days. Likely persists only *below* the wires' coverage threshold,
since Reuters and Platts run local newsrooms precisely because commodities demand it.

**4. The interpretation gap.** Everyone has the fact; nobody did the arithmetic. This project
already demonstrated one: a **28-day gap** between the ICE rule being correctly reported and being
correctly framed. Information *processing* cost, not information *acquisition* cost.

Positions 2 and 4 are the defensible ones, because neither is a speed race.

---

## 3. The reframe: nowcast a quantity, do not emit a signal

This is the load-bearing design change, and it follows directly from the failure table above.

**A signal cannot be validated.** `supply_risk = 73` has no ground truth. Every attempt to
evaluate it collapses into correlating it with price — which is exactly the procedure that
produced six wrong stories in this repo. The evaluation method was the defect.

**A state variable can be validated, because it gets published.** Total gas-fired capacity offline
in MW. Cumulative Ivorian cocoa arrivals to date. Certified stocks. FCI procurement as a
percentage of season target. Each is a real physical quantity that the market observes only at
discrete official releases — weekly, monthly, or seasonally — and that is continuously changing in
between.

So the system's output is not a trading signal. It is:

> **The number that will be officially published on date D, estimated today, with an error bar,
> assembled from N public disclosures, each cited.**

Five things follow, and together they are the whole argument:

1. **It is falsifiable in its own units.** When the official release lands, the nowcast was right
   or wrong by a measurable amount. No price correlation is involved, so none of this session's
   failure modes can occur.
2. **The benchmark already exists and is public.** Reuters and Bloomberg poll analysts before
   major releases (EIA storage, WASDE, inventory reports). **Beating the published consensus on
   the official number is a demonstrable edge that requires no backtest of a trade** — which
   sidesteps transaction costs, slippage, position sizing and overfitting entirely.
3. **It relocates the edge away from the wire.** The market prices a news item in seconds. It does
   not maintain a live estimate of a monthly series. Interpolating between official releases is a
   job nobody is racing you to do.
4. **It matches the confirmed cases exactly.** FCI procurement at 5.51% of a 44.4 Mt target on
   10 May 2022 *was* a nowcast of a quantity, published, unaggregated, three days ahead of the
   ban. The system would have carried that number as state, not as a signal.
5. **It maps cleanly onto the brief's two latency tiers.** Cached sub-second = the current state
   estimate. Minutes-level fresh inference = a new disclosure arrives and the estimate updates.
   The SLO split stops being an infrastructure detail and becomes the product.

The trader still makes the trade. We sell them the number earlier and with a stated error bar —
and, unlike a signal, we can prove whether we were any good at it.

---

## 4. What that changes in the architecture

| Old design | Redesign | Why |
|---|---|---|
| Source = a news feed | **Source = a disclosure obligation** — legal basis, publisher, deadline, format, language, historical punctuality | You can then measure **coverage of obligations**, not coverage of news. Absence becomes checkable |
| Alert on absence is an ops concern | **Absence is a signal.** A publisher legally required to publish daily that has not published is information about the publisher | The strongest form of "alert on absence" — it stops being a monitoring nicety |
| Entity resolution is layer 2 plumbing | **Entity resolution is the moat** | If the edge is aggregating fragmented publishers, then linking "Unit 3 at Gonyű" to a canonical asset with a known capacity is precisely what turns fifty facts into one number. Nothing else in the stack is hard to copy |
| LLM extracts claims | LLM **normalises, resolves and classifies**; it never estimates the quantity | Same extraction/prediction split, sharpened. Heterogeneous free text into canonical schema is a language problem. Summing MW is not |
| Output: a score | Output: **a quantity, an error bar, and the disclosures that produced it** | The error bar is the honest part. It should widen when coverage drops |
| Evaluate by price correlation | Evaluate by **nowcast error against the official release, and against published consensus** | The only evaluation in this project that cannot silently produce a wrong story |

Everything the earlier build got right survives unchanged: the two clocks, point-in-time reads,
the grounding gate, dedup, and the refusal to let the model emit a number. Those were never the
problem. **The problem was that the thing being produced could not be checked.**

---

## 5. Selection criteria for the product

Given the above, commodity choice is no longer about news volume. It is about which product
maximises positions 2 and 4, and offers a published quantity to nowcast against:

- **(a)** A **mandatory disclosure regime** — the fact is published by law on a deadline, not discovered
- **(b)** **Fragmented publishers** with incompatible formats, so no single aggregator dominates
- **(c)** A **free-text component** where an LLM beats a schema parser
- **(d)** A **language barrier** on primary sources
- **(e)** **Unparsed primary sources** nobody assembles into a time series
- **(f)** **A published official quantity** to nowcast, on a slow enough cadence that interpolation is worth something — this is now the most important criterion, because without it the system cannot be graded
- **(g)** **A tradable, liquid instrument** a non-giant can access
- **(h)** **Not already saturated** by a commercial product

Coffee scores poorly on (a), (b) and (f) — which is why the coffee build kept producing findings
that had to be retracted. The candidate scoring is under evaluation and lands in §6.

---

## 6. Candidate scoring — six commodities, and all six are weak

Scored against the criteria in §5. The honest headline is that **not one clears the bar**, and
the least-bad wins on fewest disqualifying flaws rather than on merit.

| Candidate | Verdict | What kills it |
|---|---|---|
| **Cocoa** (Ghana COCOBOD, CIV arrivals) | weak | **Reuters is the primary source** for half the CIV series — it phones brokers for the exporters'-estimate leg. A paid aggregator already sells it. And what actually mattered in 2023-24 was smuggling (~160k t) and disease, invisible in arrivals until after the fact |
| **LME base metals** | weak | Dense numeric tables — **nothing for an LLM to read**. Same-day distribution to every desk via 50+ licensees. The 2022 nickel squeeze turned on Tsingshan's **bilateral OTC short, categorically absent from any public report**: no reader of public data, however fast, would have seen it |
| **EU carbon (EUA)** | weak-moderate | The strongest regulatory-text case, and it still fails. The two price-moving events — the trilogue deal and the annual TNAC/MSR number — are **simultaneous scheduled broadcasts** at a fixed hour. Edge there is milliseconds, not comprehension. The genuinely dense documents move sector compliance costs, and CBAM's price is *pegged to* EUA rather than driving it |
| **Dry bulk freight / FFAs** | weak | Fails on access alone. BDI panellist data is a paid product; fixtures reach the public through broker circulars **after the brokers have looked**; FFAs are OTC and voice-brokered. Disqualifying regardless of data quality |
| **US gas pipeline EBBs** | weak | **The premise is false.** FERC Order 587 mandates the postings, but Genscape (now Wood Mackenzie) already sells "NatGas RT" aggregating **130+ pipelines and 20,000+ points** with alerting, and a freemium competitor exists. Not unparsed — parsed by an incumbent with a 25-year head start |
| **Refinery outages** (TCEQ/BAAQMD) | weak | **Timing inverts the thesis.** The initial notice has a 24-hour legal window; the information-rich final report lands ~two weeks later, long after crack spreads moved. The explosion itself is the signal — the filing *confirms* the news. IIR Energy already runs phone-verified tracking across 8,500 facilities |

### And the aggregation thesis was partially falsified — by its own best example

§2's position 2 claimed the durable edge is aggregating facts too small to report, because that is
not a race. **The mechanism is real; the "it stays unreported" clause is wrong.**

Genscape's Cushing crude number is exactly this thesis executed: infrared readings of individual
tanks plus pump-station sensors, aggregated into one weekly figure released a day ahead of the
official EIA number. No single tank reading is news; the aggregate is. And it became a **branded
product that Reuters has quoted by name in headline wire copy since at least 2015** — verifiable
in dated stories from Mar 2015, Feb 2016 and May 2016, each attributing the price move to
"Genscape." Verisk bought the company for **$364M in 2019**.

**When aggregation works, it gets named.** The moat was proprietary sensor access and 25 years of
continuous operation — a cost-structure moat, not an information-secrecy one. No documented case
was found of a persistently nameless aggregate quietly moving markets. "A fund with real edge
wouldn't publish it" is an unfalsifiable excuse, and should be labelled as one rather than used
to rescue the claim.

The part that survives scrutiny is narrower and still worth having: **extraction from
unstructured, multi-language, multi-publisher text with no stable schema, plus entity resolution
linking those mentions to canonical physical assets.** Both are documented as genuinely hard —
WRI's own power-plant matcher admits it "can sometimes wrongly match two power plants or fail to
match two entries for the same power plant," and S&P sells Kensho Link as a standalone product
whose only job is matching messy text to 70M canonical IDs. Neither reduces to a `GROUP BY`.

### What the literature says, which decides the whole question

- **News sentiment is dead as a standalone signal.** Priced in milliseconds to seconds by HFT
  infrastructure. Tetlock's own foundational paper found the effect **reverses within days** —
  a noise-trader proxy, not information. McLean & Pontiff's base rate for any published predictor
  is **26% lower out-of-sample, 58% lower after publication**.
- **The interpretation gap is alive, and it is the best-evidenced text edge available.**
  Jiang, Li & Wang (*JFE* 2021) find prices drift *in the same direction* for days after firm
  news with no reversal, worse when investors are distracted and analysts slow — and state the
  strategy **remains profitable after transaction costs**. Hirshleifer/Teoh and "Driven to
  Distraction" supply the mechanism: attention is scarce and allocatable.
- **Realistic effect size is IC 0.02–0.05**, giving IR ≈ 0.7 at 200 independent bets. Anything
  claiming Sharpe > 2 from public text is a red flag — and note that the two most-cited academic
  text results (Sharpe **4.29**; **22%/year**) are gross, uncapacitated backtests. Useful as
  mechanism proof, not as return targets.

### The alternative that is not a commodity at all

Four independent research tracks converged on the same conclusion by different routes: the
literature says target complex, low-attention material; REMIT says the edge is understanding a
disclosure better than a schema does, not reading it first; aggregation says the moat is
extraction plus entity resolution; the language track says the gap survives only in structured
administrative data nobody narrates. **None of them says "pick commodity X."**

So the selection axis is the **document class**, not the commodity: *where is the material
hardest to process, and where is attention thinnest?*

Which points at the single strongest idea available, and one nobody appears to have applied to
commodities:

> **Structural diff of recurring commodity documents.** Not the level, the *change in language
> between successive editions of the same publication.*

This is the "Lazy Prices" mechanism (Cohen, Malloy & Nguyen, *JoF* 2020): firms that materially
change 10-K/10-Q language show **zero announcement-day price reaction** and up to **188bp/month**
subsequent drift. The 22%/year headline is a gross academic long-short and should not be treated
as a return target — but the *mechanism* is the cleanest identification in the whole literature
of "the market had the information and did not read it." Zero same-day reaction is not
underreaction to news; it is nobody looking.

Commodities are full of recurring documents that nobody diffs: WASDE and CONAB narrative text
edition over edition, exchange rulebooks and contract specs, TSO asset descriptions, producer
annual reports, port authority tariff schedules, phytosanitary and quarantine notices. **This
project already found one instance of exactly this by accident** — the ICE rule change, where the
fact was reported the next day and correctly framed 28 days later. That is a document-diff signal
that was caught by hand.

It fits every constraint the evidence imposes. It is not a speed race — the drift accrues over
weeks. It requires language understanding rather than a schema, because the signal *is* the
change in wording. It targets the low-attention end. And it has a validation path that does not
touch price: did the changed clause subsequently matter?

### Ranking

| Rank | Alternative | Case for | Case against |
|---|---|---|---|
| **1** | **Document-diff across recurring commodity publications** | Best-evidenced mechanism in the literature; zero same-day reaction; no speed race; needs exactly what an LLM does; never publicly applied to commodities | Novel extension, not a cited commodity finding. Effect size unproven outside equities |
| **2** | **European gas/power (TTF, German baseload) via REMIT free-text + asset history** | Only candidate where mandatory disclosure is unambiguous law with a "without delay" rule; 200+ participants across 19+ countries, **1,000+ UMMs/day**; free-text "Reason for Unavailability" and "Remarks" fields **confirmed on a live record**; TTF traded ~103M contracts in 2025; and ENTSO-E/AGSI+ publish the truth, so a **nowcast can be graded** | Structured layer is commoditized twice over — free scrapers on GitHub, plus Wood Mackenzie/Genscape, Montel, Enappsys, Volue selling it. You compete on interpretation against 25-year incumbents |
| **3** | EU carbon regulatory text | Unambiguous mandate, liquid instrument | Price-moving events are simultaneous broadcasts; ICIS/Veyt/Vertis already sell same-day Brussels analysis |
| — | Cocoa, LME, freight, US gas EBBs, refinery filings | — | Each fails on a specific disqualifying flaw above |

**Honest summary: option 2 is the best *system* and option 1 is the best *idea*.** They compose —
REMIT supplies a gradeable nowcast target and a genuine free-text seam; document-diff supplies
the mechanism with the strongest evidence and no incumbent. Neither is a licence to expect more
than IC 0.02–0.05, and any claim above that should be treated as a defect.

---

## 7. How we would know we were wrong

Stated in advance, because every wrong claim in §1 was retrofitted after the fact:

- **The nowcast does not beat published consensus** on the official release, over a pre-registered
  window. Then the system is an expensive way to reproduce a free number, and should be abandoned.
- **The error bar does not widen when coverage drops.** If the stated uncertainty is insensitive to
  how many disclosures actually arrived, it is decoration.
- **Absence is never informative.** If missed publication deadlines carry no predictive content,
  that whole branch is dead weight.
- **Entity resolution turns out to be easy.** If a regex gets 95% of mentions to canonical assets,
  there is no moat and a competitor replicates the system in a fortnight.
- **The aggregate is dominated by one large publisher.** If 90% of the estimate comes from a single
  source, the fragmentation thesis is false and one subscription replaces the pipeline.

Each is measurable, and each kills a specific load-bearing claim rather than the vague whole.
