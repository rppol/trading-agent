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

## Honest limits

- **n = 1.** This is an illustration of a mechanism, not evidence about its generality. No
  statistic is quoted for the episode because none is available from a single event.
- The generality test is a separate, pre-registered question: does `Δpending` add explanatory
  power for `Δcertified` beyond an autoregressive baseline, in the post-rule regime, with the
  pre-rule regime as the control? The mechanism predicts the effect should be **weaker before
  1 December 2023**, because the queue was contaminated by re-certification. A mechanism that
  predicts its own absence is the only thing at this sample size that distinguishes a case study
  from a cherry-pick.
- **The price leg is reported as a negative result and should stay that way.** If a later test
  finds an edge here, the burden is on that test.
- `KC=F` is a spliced continuous front-month series with roll discontinuities, not official ICE
  settlements.
- Backfill `ingest_time` is not recoverable. The file's internal `As of:` stamp is the event
  time; a defensible ingest clock for archaeology is the next business morning, which
  deliberately discards up to a session of edge.

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
