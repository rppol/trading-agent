# Orchestration

Which jobs in this system are deterministic stages, which are single model calls, and which
genuinely need an agent — plus what running a large fan-out of review agents over this design
actually taught.

## 1. Agent, model call, or stage

| | Deterministic stage | Model call | Agent |
|---|---|---|---|
| Replayable byte-for-byte | **yes** | no | no |
| Plans its own steps | no | no | **yes** |
| Cost predictable | **yes** | roughly | no |

> Anything whose output must be identical on re-run is a **stage**. Anything turning
> unstructured input into a fixed schema is a **model call**, not an agent. Agency is warranted
> only when the *sequence of steps cannot be known in advance*.

Applied here, that is a short list. Ingest, dedup, triage, grounding, scoring and serving are
stages. Claim extraction is a model call — fixed schema, fixed input; giving it tools would only
add failure modes. **If you can draw the flowchart in advance, it is a pipeline**, and most of
what is marketed as an agentic commodity platform is a prompt in a loop over a RAG index.

## 2. The two jobs that do warrant agency

**The discovery agent, and it is the higher-value one.** The best findings in this project came
from diffing primary documents — a rulebook appendix adding a deliverable origin two years
forward, a spreadsheet footnote encoding a deferred discount. It is ~90% deterministic: fetch,
canonicalise, structural diff, with a model at exactly one step — *is this diff material?*
Two rules make it work: **canonicalise before diffing** (never diff bytes; PDFs re-encode and
timestamps change daily), and **the model may rank, never suppress** — removals and set
differences surface unconditionally, because asking a model whether an absence matters is how you
miss the missing line.

**The research agent.** "Why did coffee move 4% today?", with citations. Its hard requirement is
not retrieval but **calibrated abstention** — this project has shown repeatedly that confident
post-hoc attribution is the dominant failure of commodity commentary itself. An agent trained on
that corpus reproduces it by default. So the model describes and cites what a deterministic
scorer already attributed; **causation is a system output, not a model output**, and the answer
is rendered from a schema rather than free-written.

## 3. What a large review fan-out demonstrated

**Fan out by lens, not by volume.** Six reviewers were run against this artefact with six
different hostile lenses. Their findings barely overlapped: one found six mutually incompatible
cost figures, another a grounding gate that did not exist, another that the breadth arithmetic
had its sign backwards. None would have found the others'.

> A second agent with the same lens adds cost, not coverage. A second agent with a different lens
> adds coverage at the same cost.

**Divergence needs a deterministic tiebreaker, not a third opinion.** Two agents disagreed about
whether a paper modelled transaction costs. A third model would have voted, not resolved;
extracting the PDF and grepping settled it in one command. **Majority voting among models is
appropriate for judgement and actively harmful for facts**, because it converts a resolvable
question into a popularity contest among correlated readers.

**Convergence counts only across disjoint evidence.** Two agents reached the same exchange rule
change from opposite directions — one tracing a pending-grading queue, one debunking freight as
the cause of a stock collapse. That is worth something. Three agents agreeing from the *same*
corpus is one sample counted three times, and in a domain whose failure mode is repeating the
most-repeated explanation, agreement is positively correlated with being wrong.

**Track dispatched-versus-returned.** Agents stall and die; several did here. A crashed agent is a
**gap in coverage, not a null result**, and one crashed question went silently missing from the
synthesis — the same "nobody looked ≠ nothing there" failure the rest of this register is about.

**The integrator is the weakest link and nobody audits it.** Every substantive error in this
project was made by the synthesising layer, not by a specialist: a figure taken from a summary
and promoted to a headline, a batch size generalised from one observation, an inference the data
in hand already refuted. The specialists each had one narrow job; the integrator had context,
pressure and a narrative to maintain. **The synthesis layer needs its own adversarial review, and
it will never request one.**

## 4. Production shape

Scheduling is calendar-driven for primary documents, batched on arrival for extraction,
synchronous only for the research agent. Every run is keyed and idempotent because retries are
the normal case; concurrency caps are a **cost** control, not a performance one; and a hard
per-run budget degrades to a deterministic path rather than to silence.

**No workflow engine yet.** At this scale it is a scheduler, a queue and a results table. Adopt
durable execution when agent runs routinely exceed an hour and must survive deploys, or when you
have written a bespoke resume-from-step-N path for the third time.

**Agents never write to the claim ledger.** Output lands in a proposals table; promotion is a
separate, deterministic, reviewed step. That is what keeps the replayable core clean while
non-deterministic things run beside it.

## 5. Where this maps onto the product

| Orchestration | Product |
|---|---|
| Fan out by lens | Corroboration across text, AIS, imagery |
| Convergence across disjoint evidence | Cross-modal agreement gating conviction |
| Deterministic tiebreaker on disagreement | The verbatim-span gate |
| Track dispatched-vs-returned | Alert on absence, not just on error |
| The integrator is the weakest link | Aggregation is where lookahead hides |

Both are systems for forming beliefs from unreliable sources, and both fail the same way: they
accept a fluent summary in place of a checkable fact. Neither is fixed by vigilance.
