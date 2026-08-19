# Case study: the rule change that drained the warehouses

A worked example, reconstructed from free point-in-time data, of a genuinely buried signal that
moved a widely-watched number — and did not move the price.

It is not a success story. It is the more useful thing: a **verified mechanism with no
tradeable edge**, which is the outcome this system is most likely to produce and the one a
research platform has to be honest about.

---

## The setup

In late 2023 ICE certified arabica stocks collapsed to a **24-year low**. The trade press read
it as a supply crisis. Coffee was disappearing from the exchange's warehouses just as Brazil and
Vietnam were having a bad year, and the price went up.

Almost none of that was what it looked like.

## What was actually happening

On **29 September 2023** ICE filed an amendment to its certification rules: coffee that had been
certificated and then de-certificated could no longer be re-submitted for grading. Requests were
accepted only through **30 November 2023**, and the rule took effect **1 December 2023**.

That is an administrative deadline, and it does what administrative deadlines do — it changed
the timing of a queue, not the quantity of coffee in the world.

Reconstructed from the free daily ICE file (`coffee_cert_stock_YYYYMMDD.xls`, deterministic
public URL, no auth, available back to 2016):

| Date | Certified bags | Pending grading | |
|---|---:|---:|---|
| 2023-09-15 | 445,913 | 17,755 | |
| **2023-09-29** | 441,945 | 10,011 | **ICE files the rule amendment** |
| 2023-10-16 | 434,772 | 2,240 | |
| 2023-10-31 | 389,138 | **0** | queue empty |
| 2023-11-15 | 297,100 | 7,265 | |
| 2023-11-29 | 259,800 | 28,090 | day before the deadline |
| **2023-12-01** | **224,066** | 26,985 | **rule effective — the 24-year low** |
| 2023-12-15 | 242,399 | 30,890 | |
| 2024-01-16 | 259,190 | 53,180 | |
| 2024-02-15 | 302,462 | 63,477 | |
| **2024-04-15** | **624,545** | 66,079 | **+179% off the trough** |

The headline number fell **49%**. The queue behind it went from **zero to 66,079 bags**. Stocks
then nearly **tripled** in four months.

**The pending-grading queue is the buried signal.** It is the physical line between "coffee has
landed at a licensed warehouse" and "coffee is deliverable against the contract". It sits in the
same free file as the number everybody quotes, three sections further down, and it mechanically
leads that number by weeks. While the market was reading a 24-year low as scarcity, the queue
was saying the coffee was already on the dock.

*(A small demonstration of the primary-source argument: the 224,066-bag figure circulates widely
and secondary sources place it variously in November and December 2023. It is 1 December 2023.
Read from the file.)*

---

## And the trade loses money anyway

Here is where the case study earns its place.

| Window | Certified stocks | KC=F |
|---|---|---|
| 31 Oct → 1 Dec 2023 | 389,138 → 224,066 (**−42%**) | 167.30 → 193.90 (**+15.9%**) |
| 1 Dec 2023 → 15 Apr 2024 | 224,066 → 624,545 (**+179%**) | 193.90 → 231.55 (**+19.4%**) |

The naive read of the buried signal is: *the queue is building, the stocks are coming back, the
scarcity is administrative — sell the squeeze.* **Coffee rose another 19.4% while the warehouses
refilled.**

Prices went up while stocks collapsed, and up again while stocks nearly tripled. Over this
window the certified stock level was **not** what set the price. The 2023–24 Brazilian and
Vietnamese supply story was, and it ran straight through both halves.

**A caveat on those two percentages.** `KC=F` is a spliced continuous front-month series, so a
change measured across a roll date includes the contract spread as well as the price move. Both
windows above span rolls, and arabica rolls are large — backwardation has been extreme. The
*levels* are sound (an independent check reproduces a known record settlement to the cent) and
the *direction* is not in doubt: prices rose in both halves either way, which is the whole
point. But the precise magnitudes should not be quoted as clean returns. A single-contract
series, or a ratio-adjusted splice, is required before anyone puts a number on the edge.

---

## What this actually demonstrates

**1. The signal was real, buried, free, and correct — about the physical world.** The queue
predicted the stock rebuild weeks ahead. That is a genuine informational edge over anyone reading
only the headline number, and it cost nothing to obtain.

**2. Being right about the world is not the same as being right about the price.** This is the
concrete instance of the argument in [ARCHITECTURE §1b](ARCHITECTURE.md): a supply-side indicator
can be accurate and still carry no tradeable information, because the price is already being set
by a larger factor the indicator says nothing about.

**3. It was never a news problem.** The disambiguating document was an exchange rule filing. The
disambiguating data was a spreadsheet on a public URL. Neither is in the news corpus at any
volume — [MEASUREMENTS.md](MEASUREMENTS.md) records that wire and institutional domains are at
hard zero in 675,840 GDELT documents. A better extractor, a better prompt or a bigger model would
not have found this. **A cron job and a parser would have.**

**4. The interpretation trap is the real lesson.** The queue in October–November 2023 was
substantially *recycled* inventory racing a deadline, not new supply arriving. The same number
means opposite things either side of 1 December 2023, and the only way to know which is to have
read the rule. **An indicator without its institutional context is a number, not a signal** — and
no amount of statistical sophistication recovers the context.

---

## The generality test, run

The episode above is n = 1. The pre-registered question was whether the queue leads the number
in general, or whether December 2023 was a coincidence dressed as a mechanism.

Across **182 observations, January 2021 – August 2026**, pending grading as a share of certified
stock, regressed against the **forward** change in certified stock, with two controls:

| Horizon | pending/cert → forward change | certified **level** (mean-reversion control) | trailing change (momentum control) |
|---|---:|---:|---:|
| 14 days | **+0.644** | +0.362 | +0.592 |
| 28 days | **+0.606** | +0.321 | +0.522 |
| 42 days | **+0.583** | +0.300 | +0.320 |

It beats both controls at every horizon, and the margin **widens** at 42 days — so it is not
simply momentum in the certified series wearing a different name.

Two further dated episodes outside the 2023 window, from the same series:

- **November 2022.** Certified stocks hit a 23-year low of 384,795 on 2 Nov. Pending grading went
  3,436 (17 Oct) → 142,176 (2 Nov) → **577,099 (16 Nov)**. Certified then rebuilt to 753,981 by
  16 December. The queue announced, with roughly the right magnitude, that the "record low
  stocks" bull story was about to be buried.
- **May–June 2026.** The queue fell to **literally zero** — the file prints "No Grading Pending"
  on 2 June — and certified stocks bled every session from 462,777 to 229,214, **−50%**.

**And the honest limit, which is large.** Part of this correlation is an **accounting identity**:
bags in the queue that pass grading *become* certified bags. It is a leading indicator of the
**number**, not independent information about **supply**. Three things stop it being purely
mechanical — bags fail grading, the queue is silent about withdrawals (which is what actually
drives drawdowns), and de-certified coffee can be re-submitted, so pending bags are not
necessarily new coffee. Its value is **timing, not insight**, and that distinction should survive
into any use of it.
- **The price leg is reported as a negative result and should stay that way.** If a later test
  finds an edge here, the burden is on that test.
- `KC=F` is a spliced continuous front-month series with roll discontinuities, not official ICE
  settlements. Any differenced analysis on it picks up artificial jumps at roll boundaries; the
  kill battery's K2 has this exposure and it is one more reason its n=6 result is reported as a
  harness check rather than a finding.
- **Regime breaks contaminate the obvious follow-up window.** A 2025 replication would straddle
  a tariff imposed in August and removed in November, during which certified stocks fell ~52% and
  turned up the month the tariff went. Stock and price are jointly driven by the policy event
  there, so a naive lead-lag reads a common cause as one leading the other. That window needs a
  regime split, not a longer sample.
- Backfill `ingest_time` is not recoverable. The file's internal `As of:` stamp is the event
  time; a defensible ingest clock for archaeology is the next business morning, which
  deliberately discards up to a session of edge.

## The level is a trap, and this is the part worth publishing

The naive companion story — "low certified stocks are bullish" — is not merely unproven. It has
the wrong sign at the two moments it is most often quoted:

| | Certified stocks | What KC did next |
|---|---|---|
| Jul 2021 | multi-year **high**, 2,188,158 bags | rallied to **260.45** by Feb 2022 |
| Nov 2022 | **23-year low**, 382,695 bags | fell to **142.05** by Jan 2023, **−45.5%** |
| Mar–Jun 2026 | **−25% drawdown** | fell ~25% to its low of **238.85** on 9 Jun |

Record-low stocks preceded a 45% decline. A multi-year high preceded a 70% rally. The 2026
drawdown gave a wrong-way signal for three months before it gave a right-way one.

**Certified stocks are a conditioning variable, not a signal.** They govern how violently the
market reacts to a weather headline; they do not generate the headline. Anyone backtesting
"stocks down, buy" will find those two episodes destroy it — which is the same conclusion, from
the opposite direction, as the price legs above.

One compositional fact nobody quotes: **Brazil's share of certified arabica fell from 49.7%
(941,210 bags, April 2021) to 2.8% (6,428 bags, August 2026).** Honduras, Peru, Uganda and Mexico
now dominate the deliverable pool. The benchmark's certified stock has very little to do with the
crop the market actually prices.

## A better buried signal, found while looking for this one

The strongest genuinely-buried item surfaced in this whole exercise is not in the news, the price
series or the stock file. It is in the **rulebook**.

ICE is adding **Vietnam as a deliverable origin against the Coffee "C" arabica contract**, at
**−600 points** — the same discount as Brazil — effective with the **May 2027** contract. Board
approved 27 March 2025, effective 15 April 2025, published in a rulebook appendix and a one-page
exchange notice.

The world's largest coffee exporter becoming deliverable against the world arabica benchmark is a
structural change to the deliverable supply pool, **dated two years forward**, that a
2027-expiry position can express. It is free, public, and permanently observable — and it is in a
PDF appendix that no news pipeline reads.

The same rulebook carries a second one: a **Transition Stocks Discount**, escalating to
**900 points (9 c/lb) by December 2028**, applying to coffee without validated deforestation
due-diligence. On 18 August 2026 that was **161,137 of 229,214 certified bags — 70.3%** of the
deliverable pool. The schedule has been deferred twice, each time tracking an EU regulatory
delay, and you can watch the deferral happen in **two sentences of a spreadsheet footnote** that
changed between September 2025 and June 2026.

Neither has a demonstrated price move attached, and neither is claimed to. They are recorded
because they are exactly the shape this system should be built to catch and the news pipeline
structurally cannot: **dated, mechanical, forward-known changes to contract economics, published
in primary documents nobody parses.**

## Reproducing it

```bash
python -m signals.ice_stocks 60        # fetch and parse the daily file
python -m signals.kill_tests           # the battery, against real KC settles
```

The parser is section-aware because it has to be: the report's own layout changed between 2023
and 2024 — `BAGS CERTIFIED` became `TOTAL BAGS CERTIFIED`, and a transition-bags section appeared
that did not previously exist. A parser keyed to the later string silently returned nothing for
every earlier file: fetch succeeded, parse failed, the series just stopped. That is the same
silent-absence failure as everything else in [FAILURE_MODES.md](FAILURE_MODES.md), and it is why
that register exists.
