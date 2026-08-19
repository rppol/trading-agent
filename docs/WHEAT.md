# Wheat: the second commodity, and what it costs

The architecture claims the marginal cost of commodity N+1 is near zero. The brief names two
commodities — coffee and wheat — so the claim is testable rather than rhetorical. This document
tests it, and the claim does not survive in the form it was written.

Everything below carries a source. Anything not independently verified is marked **UNVERIFIED**
rather than asserted, because the failure mode this whole project is built against is the
plausible claim nobody checked.

---

## 1. How the measurement was wrong before the answer was

The first attempt at this test counted **coffee-specific lines in the existing code**: 41 of
1,458, about 3%, almost all of it lexicon and enums. The conclusion drawn was that the pipeline
is 97% commodity-agnostic and wheat is mostly a config row.

**That measurement cannot see what it needs to see.** It counts how much coffee-specific code
*exists*; the question is how much wheat-specific code is *missing*. A pipeline with no concept
of a government as a market participant scores zero coffee-specific lines in that area — which
reads as portable and means absent. Survivorship, exactly: the measurement surveys the code that
got written and infers something about the code that did not.

The correct test is to take a second commodity's real structure and ask what the existing
pipeline could not grade. That is the rest of this document.

---

## 2. What structurally differs

| Axis | Coffee | Wheat | Source |
|---|---|---|---|
| Exchange venues | 2 (ICE Arabica "C", ICE Robusta) | **5** — CBOT SRW (`ZW`); KC HRW as ticker **`KE`** on CME Globex (CBOT absorbed KCBT in 2013 — "KC" is a legacy name, not a separate venue); HRS on **MIAX Futures** (formerly MGEX, migrated off Globex to its own engine in 2026); Euronext Paris milling (`EBM`); CME Black Sea CVB (Argus), first traded 2 Jun 2025 and thin | [CME KC](https://www.cmegroup.com/markets/agriculture/grains/kc-wheat.calendar.html) · [MIAX](https://www.miaxglobal.com/market/proprietary-products/minneapolis-hard-red-spring-wheat-products) · [Euronext](https://live.euronext.com/en/product/commodities-futures/EBM-DPAR/contract-specification) · [CME CVB](https://www.cmegroup.com/articles/faqs/faq-black-sea-wheat-cvb-argus-futures-and-options.html) |
| Quality classes | 2, near-binary | **≥5** (SRW, HRW, HRS, White, Durum), each with its own protein curve. HRW basis runs 35c/bu at 11% protein, $1.05 at 12%, $1.33 at 13%, **$1.83 at 14%** — a quality story moves a cash number by >$1/bu with flat CBOT untouched | [Farm Progress](https://www.farmprogress.com/corn/protein-increases-the-price-of-wheat) |
| Substitution | none | real and price-gated: wheat-corn feed switching activates as the cash gap narrows to **~$0.50/bu**. A pure corn-side shock moves wheat demand with zero wheat-side news | [U.S. Wheat](https://uswheat.org/wheatletter/u-s-wheat-prices-competitive-with-corn-for-domestic-feed-use/) |
| Government stockpiles | none | China alone holds **~121 Mt (2026/27), 44–51% of world stocks** — a non-market actor larger than most producers | [Farm Online](https://www.farmonline.com.au/story/9253999/global-grain-stocks-chinas-vast-reserves-distort-world-supply/) |
| Export bans | none | frequent and abrupt. India banned exports **13 May 2022**; CBOT SRW **+5.9% to $12.47/bu** the next session, July contract limit-up | [FAS GAIN](https://www.fas.usda.gov/data/india-india-bans-wheat-exports-due-domestic-supply-concerns) |
| State buying | none | Egypt's GASC tenders are price-moving events; a **3.8 Mt** tender, and a record **4.72 Mt** domestic purchase in 2026 | [FAS GAIN 2026](https://www.fas.usda.gov/data/gain/2026/05/egypt-egyptian-wheat-procurement-price-increase-2026-season) |
| Harvest topology | perennial, continuous | annual bulk in **two hemispheric windows** — N. hemisphere Jun–Aug, S. hemisphere Nov–Jan. ABARES cut Australia's 2019 forecast **19.1 Mt (Sep) to 15.9 Mt (Dec)** inside one window | [ABC](https://www.abc.net.au/news/rural/2019-12-03/abares-crop-report-forecasts-winter-production-slump/11758410) |

---

## 3. The instrument map, and why it re-confirms the coffee finding

The coffee work concluded that a regional shock shows up in a **differential**, not in flat
price. Wheat says the same thing on independent evidence, with one important exception.

| Claim type | Instrument | Evidence |
|---|---|---|
| Localized quality shock | **protein premium curve** (cash basis by protein %) | priced off-exchange entirely; the ladder above |
| Hard-vs-soft class imbalance | **class spread** `KE − ZW`, actively traded | HRW-premium to mid-2015, near parity 2015–19, then **inverted negative** 2019–late 2021 with KE 65–75c/bu *under* ZW — a multi-year regime shift per CME's own retrospective ([CME](https://www.cmegroup.com/education/articles-and-reports/kc-vs-chicago-wheat-spread-a-tale-of-two-markets.html)) |
| Regional export-policy shock | **inter-exchange spread** ZW vs EBM vs CVB | Russia's duty = 70% x (reference − indicative), recomputed **weekly**; it hit zero in Jul 2025. A Black-Sea-origin lever with no mechanism to move CBOT SRW ([Bloomberg](https://www.bloomberg.com/news/articles/2025-07-05/russia-drops-wheat-export-duty-to-zero-in-bid-to-boost-sales)) |
| Port/logistics constraint | **export basis** (FOB cash − futures), per port | U.S. Wheat publishes Gulf/PNW/Great Lakes basis weekly; "historically low PNW HRS export basis" is reported as a signal distinct from flat HRS futures ([USW](https://uswheat.org/market-information/price-report/)) |
| **Corridor collapse at global scale** | **flat price is correct here** | Black Sea Grain Initiative carried ~33 Mt to 45 countries. Russia withdrew 17 Jul 2023; CBOT **+3.5% to $6.84/bu same day**. **This is the exception, and it is gated by origin size relative to world trade, not by geography.** ([CNBC](https://www.cnbc.com/2023/07/17/russia-says-it-will-not-extend-the-landmark-ukraine-grain-deal.html)) |
| Near-term tightness | calendar spread (Dec/Mar) | mechanism sound, **no dated wheat inversion episode found — UNVERIFIED** |

The exception is the useful part. "Regional shocks live in spreads" is not a law, it is a
statement about the shocked origin's share of world trade. Colombia is a differential story;
the Black Sea is large enough to be a flat-price story. The rule needs that threshold written
into it or it will misroute the next big one.

---

## 4. Free point-in-time sources

| Source | Gives | Cadence | Machine-readable |
|---|---|---|---|
| [USDA WASDE](https://usda.library.cornell.edu/concern/publications/3t945q76s) | global S&D by country | monthly, noon ET | **yes** — Cornell archives full text + xlsx |
| [FAS ESRQS](https://www.fas.usda.gov/newsroom/usda-will-launch-new-export-sales-reporting-and-query-system-esrqs-thursday-march-26-2026) | weekly export sales **by class** and destination | Thu 08:30 ET | API advertised; **endpoint not independently fetched — UNVERIFIED** |
| [CFTC COT](https://www.cftc.gov/dea/futures/ag_lf.htm) | positioning, **SRW and HRW as separate line items** | weekly, Fri, as-of Tue | **yes** — same two-clock shape as coffee, already handled |
| [USDA AMS GTR](https://www.ams.usda.gov/services/transportation-analysis/gtr-datasets) | rail car orders, shuttle bid premiums | weekly | **partially** |
| Russia Ag Ministry duty bulletin | weekly duty RUB/t | weekly | no — Russian-language HTML |
| [Argentina DJVE](https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/exportaciones/) | export sworn declarations | near-daily | no. **Confirmed absent from the datos.gob.ar Series API** — a genuinely new connector, not a reuse |
| [ABARES](https://www.agriculture.gov.au/abares/products/release-schedule) | production forecasts by state | quarterly | no — complements the already-built ABS SDMX path |
| [FCI procurement](https://fci.gov.in/procurements.php) | state-wise procurement vs target | in-season | unclear; site restructured since 2022 |

**No clean wheat equivalent of "an obscure rulebook appendix nobody parses" was confirmed.** The
closest candidates — the Russian duty bulletin, the GTR rail premiums, FCI bulletins — are either
coincident rather than leading, or not proven to have beaten official numbers. Recorded as an
open gap, not a finding.

---

## 5. AIS actually works on bulk grain — with a caveat that matters

This is where wheat is genuinely *better* than coffee, and the mechanism is verified rather than
assumed. Bulk carrier draught changes measurably with cargo load, and draught survey is the
industry-standard way bulk cargo is weighed and invoiced, to roughly **0.5% accuracy**
([Wärtsilä](https://www.wartsila.com/encyclopedia/term/draft-survey)); the AIS inference is
peer-reviewed (Jia, Prakash & Smith, *Int. J. Shipping and Transport Logistics* 11(1), 2019) and
commercially productized ([Kpler](https://www.kpler.com/product/commodities/dry-bulk-flows-and-insight)).

Coffee moves in containers, where draught tells you nothing about any single commodity — a
20,000-TEU vessel mixes thousands of consignors' cargo at different densities in identical box
footprints, so there is no solvable inverse. (Reasoned from the mechanism; **no vendor states
this explicitly — flag as inference, not citation.**)

**The caveats are real and should be stated before anyone budgets for this.** Free AIS tiers give
position and current draught only; payload-grade analytics are enterprise-priced. AIS alone does
not identify the commodity — a Panamax could be wheat, corn or soy, and disambiguation needs load
port plus season plus known trade lane. And **no dated instance was found where AIS led an
official wheat export number.** The mechanism is sound and the vendors are real; the "AIS beat
the government by N days" exhibit does not exist in what was checked.

What free tiers realistically support: vessel-count-at-anchorage off a named export port as a
loading-backlog proxy, and departure draught-delta as a binary loaded/not-loaded flag. Not a
calibrated tonnage number.

---

## 6. Buried signals: one confirmed, two debunked

**CONFIRMED — India, and it is the same shape as the Colombian rust finding.** By 10 May 2022 the
FCI had procured **5.51% of a 44.4 Mt season target**; the season finished near 18.7–19.5 Mt
against 43.44 Mt the prior year, a **>50% shortfall**, all of it publicly reported *before* the
13 May export ban. The press still called the ban a "surprising U-turn"
([Deccan Herald](https://www.deccanherald.com/opinion/indias-surprising-u-turn-to-ban-wheat-exports-1109662.html)),
and CBOT went +5.9% with the July contract limit-up. A public, unparsed primary-source trail
preceded a market surprise — structurally identical to the coffee case, on a different continent
and a different mechanism. *(Caveat: the 2022 FCI bulletin URL could not be pinned; the site was
restructured. Numbers corroborated by two independent outlets — **UNVERIFIED at the link level**.)*

**DEBUNKED — Black Sea Grain Initiative deadlines.** Every deadline (22 Jul 2022, 19 Nov 2022,
18 Mar 2023, 17 May 2023, 17 Jul 2023) was calendar-visible in advance, universally watched, and
Russia had signalled intent for weeks; the +3.5% move partly reversed intraday. **Do not build a
BSGI-deadline alert expecting alpha.** This is the structural opposite of buried, and it is worth
recording because it is exactly the kind of candidate that looks compelling in hindsight.

**DEBUNKED — the protein-premium parallel, and the inversion is instructive.** The intuitive
version (drought → scarce high-protein wheat → premium spikes) runs backwards: **drought raises
protein content crop-wide**, so high-protein wheat gets *more* abundant and the premium
**narrows** ([Farm Progress](https://www.farmprogress.com/marketing/wheat-farmers-are-paying-for-americans-protein-fixation)).
The shape that made the coffee differential work — a shock to one origin's yield that leaves
everyone else's quality unchanged — does not map onto a crop-wide abiotic stressor. The premium
ladder remains a valid instrument for *localized* quality shocks; it is simply not a drought
instrument. Specific dated AMS cash-premium numbers **not obtained — UNVERIFIED**.

**PARTIAL — rail logistics.** BNSF unfilled grain-car orders rose **>110,000 (+546%)** from Q2
2021 to Q2 2022, and BNSF/UP — 64% of grain rail cars — shipped 9% and 14% fewer cars year on year
([Farm Bureau](https://www.fb.org/intel/markets/rail-order-delays-empty-exports-and-equipment-shortages-transportation-disruptions-persist)).
The GTR is a real weekly primary document almost nobody parses. But **no source timestamps
"basis widened on date X, flat price moved on date Y"** — the lead-time claim is logically sound
and numerically unproven.

---

## 7. So what does N+1 actually cost

| Transfers as-is | Must be built |
|---|---|
| Claim schema (claim → instrument → confidence) | **Multi-venue resolver.** Origin → venue across 5 exchanges is routing logic, not a lookup row |
| Two clocks (event_time / ingest_time) | **2D class-spread engine.** Coffee's differential model is origin-only; wheat is origin × protein class |
| Grounding gate | **Government-action ingestion.** Export bans, state tenders, stockpile disclosures — the pipeline has no concept of a government as a market participant, and wheat needs it for at least four countries |
| Dedup, novelty | **Substitution watch.** A corn-side shock must be able to generate a wheat claim; the design never contemplated cross-commodity propagation |
| Point-in-time reads | **Two-hemisphere seasonal calendar**, gating which claims are physically plausible when |

**Verdict: the mandate holds for the outer scaffolding and fails for the pipeline.** Claim
schema, clocks, grounding gate and dedup genuinely transfer, and that is worth having — they are
the parts that took the longest to get right and the parts most likely to be wrong if rebuilt.
But three new subsystems, one cross-commodity dependency and a seasonal calendar stand between a
wheat document and a graded wheat claim.

If the architecture keeps the "N+1 is nearly free" language it must be scoped explicitly to the
scaffolding. Claiming full pipeline reuse is an overclaim that the brief's own second commodity
falsifies.

---

## Open gaps, recorded rather than resolved

- Wheat calendar-spread inversion example — mechanism only, no dated case.
- Wheat's equivalent of an obscure unparsed primary document — not confidently identified.
- Argentine DJVE filing requirement for wheat *grain* after the June 2024 reform — unresolved (the reform eliminated DJVE for wheat *bran* specifically).
- CME Black Sea CVB — launched Jun 2025 and thin; treat tradability as provisional.
- IGC Grain Market Indicator free tier — page returned a server error on fetch; re-check manually before citing.
- AIS leading an official wheat number — mechanism confirmed, dated precedent not found.
