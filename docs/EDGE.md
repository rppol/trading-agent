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

## 6. Candidate scoring

*In progress — five research tracks running against the criteria above. This section will carry
the scored candidates and the chosen product, or an honest verdict that none of them clears the
bar.*

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
