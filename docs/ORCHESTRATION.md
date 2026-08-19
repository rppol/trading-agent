# Orchestration

How a system of models, agents and deterministic stages actually fits together — and which
of those three each job should be.

This section has an unusual evidence base. The document you are reading was itself produced by a
multi-agent process: roughly twenty specialist agents researching, auditing and adversarially
reviewing, with a human-directed orchestrator integrating. **Every claim below about what works
was observed in that process, including the failures.** That is not a rhetorical flourish; it is
the only part of this design that has been run at scale.

---

## 1. Agent, pipeline stage, or neither

The word "agent" is doing enormous marketing work in this industry. The distinction that
matters operationally:

| | Deterministic stage | Model call | Agent |
|---|---|---|---|
| Replayable byte-for-byte | **yes** | no | no |
| Plans its own steps | no | no | **yes** |
| Uses tools | n/a | no | **yes** |
| Cost predictable | **yes** | roughly | no |
| Failure mode | exception | wrong answer | wrong answer, expensively, several steps later |

**The rule this system uses:**

> Anything whose output must be identical on re-run is a **deterministic stage**.
> Anything that turns unstructured input into a fixed schema is a **model call**, not an agent.
> Agency is warranted only when the *sequence of steps cannot be known in advance*.

Applied honestly to this platform, that is a short list. Ingest, dedup, relevance triage,
grounding, scoring, aggregation and serving are all **stages**. Claim extraction is a **model
call** — it has a fixed schema and a fixed input, and giving it tools would only add failure
modes. Two jobs genuinely need agency, and both are discussed below.

**Most of what is marketed as an agentic commodity platform is a prompt in a loop over a RAG
index.** The test is simple: if you can draw the flowchart in advance, it is a pipeline.

---

## 2. The two jobs that genuinely warrant an agent

### The discovery agent — and it is the higher-value one

The best findings in this entire project came from **diffing primary documents**:

- an exchange rulebook appendix adding Vietnam as a deliverable origin, dated two years forward
- two sentences in a spreadsheet footnote that changed, encoding a one-year deferral of a
  discount applying to 70% of deliverable stock
- a tariff annex with exactly one coffee HTS line missing, six weeks before the final action

None of these were in the news. All were free, public and permanently observable. **This is the
system's highest-value agent, and it is mostly deterministic**: fetch on a schedule, normalise,
diff, and use a model only at the single step that genuinely needs judgement — *is this diff
material?* Everything else is `curl` and a text comparison.

The design consequence is worth stating plainly: the model is the **smallest** component of the
most valuable agent.

### The research agent

"Why did coffee move 4% today?", answered in ninety seconds with citations. This needs real
agency because the retrieval path is not knowable in advance — the answer might live in the
claim ledger, a stock file, a positioning report or a weather run.

Its hardest requirement is not retrieval. **It is refusing to fabricate a causal story**, which
this project has repeatedly shown is the dominant failure mode of commodity commentary itself:
currency explanations that flip sign between years, rust blamed for a rally two years after it
was priced, fertiliser blamed for a crop that came in 19% up. An agent trained on that corpus
will reproduce its confident post-hoc attribution by default.

So the research agent's evaluation is mostly about **calibrated abstention**: does it say "the
move is not explained by anything in the ledger" when that is true? A research agent that always
has an answer is worse than useless, because it is indistinguishable from the commentary it
replaces.

---

## 3. What the session actually demonstrated

### Fan out by lens, not by volume

Six reviewers were run against the same artefact, each with a different hostile lens: attack the
headline claim, audit the numbers, audit code-against-docs, find what is missing, review
architecture against alternatives, judge it as a whole.

**Their findings barely overlapped.** The numbers auditor found six mutually incompatible
per-document costs. The code auditor found a grounding gate that did not exist. The
architecture reviewer found the breadth arithmetic had its sign backwards. None of them would
have found the others' defects, because they were not looking there.

> **A second agent with the same lens adds cost, not coverage. A second agent with a different
> lens adds coverage at the same cost.**

This is the single most transferable finding, and it inverts the intuitive scaling move
(more agents on the same question).

### Convergence across independent lenses is evidence

Two agents reached the same conclusion — that an ICE rule change drained certified stocks in
November 2023 — from opposite directions. One was tracing the New York pending-grading queue.
The other was debunking Red Sea freight as the cause of the London robusta collapse. Neither saw
the other's work.

That agreement is worth substantially more than either report alone, and it is cheap to arrange:
**give two agents different questions whose answers must be consistent if either is right.**

The same principle is already in the product design as cross-modal corroboration. It works for
agents for the same reason it works for text-versus-satellite: independent paths to one
conclusion are hard to fake.

### Divergence needs a deterministic tiebreaker, not a third opinion

Two agents disagreed about whether a published paper modelled transaction costs. One said it
did not. One quoted a sentence saying it did.

**A third model would have voted. It would not have resolved.** What resolved it was extracting
the PDF's text stream and running `grep` — one command, unambiguous, and it showed the second
agent was right and the document's published claim was false.

> **When models disagree about a checkable fact, escalate to a deterministic check, never to
> another model.**

This is the orchestration form of the verbatim-span gate, and it generalises: majority voting
among models is appropriate for judgement and actively harmful for facts, because it converts a
resolvable question into a popularity contest among correlated readers.

### Agents find what self-review structurally cannot

The tests in this repository reimplemented the grounding gate inline and asserted against their
own copy. They passed. They would have passed if the gate had been deleted entirely — and in
effect it had been, since the number check was `X or True`.

**No amount of re-reading my own work would have found that**, because the error was in the
relationship between two artefacts I had written to agree with each other. It took an outsider
reading the code against the documentation with no stake in either.

The production analogue: **the eval harness must be written by someone who did not write the
prompt**, or it will encode the same assumptions.

### Agents die, and the orchestrator must not

Of roughly twenty agents dispatched, **two stalled and were killed by a watchdog** after
producing partial work, and one returned a report whose central premise it had been unable to
verify because it was rate-limited mid-task.

This is normal, not exceptional, and it has three design consequences:

1. **Partial results must be usable.** An agent that dies having verified three of five claims
   should surface the three. Structure the task so intermediate findings are independently
   valuable.
2. **The orchestrator must never block on a single agent.** Dispatch, continue, integrate on
   arrival.
3. **A crashed agent is a gap in coverage, not a null result.** One of the two failures here was
   the Central American rust question, which was then silently absent from the synthesis until
   someone noticed. **Track dispatched-versus-returned explicitly**, or the orchestrator
   confuses "nobody looked" with "nothing there" — the same silent-absence failure that runs
   through the whole failure-mode register.

### The orchestrator is the weakest link, and it is the one nobody audits

Every substantive error in this project was made by the orchestrating layer, not by a specialist:

- a figure taken from a model's summary of a paper and promoted to a headline, twice
- a batch size generalised from a single observation
- a filter's precision estimated rather than measured
- an inference ("Reuters absent as a domain, therefore no wire content") that the data in hand
  already refuted

The specialists were, on balance, more careful than the integrator — because each had one narrow
job and the integrator had context, pressure and a narrative to maintain. **Design for that: the
synthesis layer needs its own adversarial review, and it will not request one.**

---

## 4. Production orchestration

### Scheduling and triggering

| Class | Trigger | Why |
|---|---|---|
| Primary-document watch | cron, per-source cadence | Rulebooks, stock files and statistical releases publish on schedules |
| Claim extraction | arrival of new documents, batched | Cost is amortised over the batch; latency budget is minutes |
| Research agent | user request | The only genuinely interactive path |
| Reconciliation | weekly, after authoritative releases | Scores prior claims against what printed |

### Failure, idempotency and cost

- **Every agent run is keyed and idempotent.** A re-run with the same inputs must be safe,
  because retries are the normal case.
- **Concurrency is capped, and the cap is a cost control, not a performance one.** Twenty agents
  in parallel is a bill, and the orchestrator is the only place that can see the total.
- **A hard per-run budget with a circuit breaker.** An agent that plans its own steps can plan
  expensive ones. The breaker must degrade to a cheap deterministic path, never to silence.
- **Tracing is per-step, not per-run.** A failed agent's value is entirely in what it did before
  it failed, which is only recoverable if each step was recorded.

### What not to build

A workflow engine, at this scale. The orchestration described here is a scheduler, a queue and a
results table. Reach for a distributed workflow system when there are genuine long-running
multi-day agent graphs with human approval steps in the middle — not before. The same trigger
discipline applies as everywhere else in this design.

---

## 5. Where this maps onto the product

The parallels are exact, and not coincidental — both are systems for forming beliefs from
unreliable sources:

| Orchestration | Product |
|---|---|
| Fan out by lens | Multi-modal corroboration across text, AIS, imagery |
| Convergence across independent paths | Cross-modal agreement gating conviction |
| Deterministic tiebreaker on disagreement | The verbatim-span gate |
| Track dispatched-vs-returned | Alert on absence, not just on error |
| Partial results are usable | Provisional signals with explicit staleness |
| The integrator is the weakest link | The aggregation layer is where lookahead hides |

**The system and the process that built it fail the same way**: both are tempted to accept a
fluent summary in place of a checkable fact, and both need a mechanical control rather than
vigilance to stop it.
