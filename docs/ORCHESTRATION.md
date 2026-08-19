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

---

## 6. The evidence, since these patterns are mostly chosen by fashion

Every pattern below was checked against published work rather than intuition. Two of the four
findings run against what this document originally assumed.

### Chain-of-thought: skip it on the extraction call

**"To CoT or not to CoT?"** (Sprague et al., [arXiv:2409.12183](https://arxiv.org/abs/2409.12183),
ICLR 2025) — a meta-analysis over 100+ papers plus fresh evaluation across 20 datasets and 14
models. CoT delivers large gains **almost exclusively on math and symbolic reasoning**; elsewhere
gains are "negligible or negative." On MMLU it roughly equals direct answering *unless the
question contains an `=` sign* — that is, unless it is secretly a maths problem.

Claim extraction is classification plus span location. It is exactly the category the
meta-analysis says CoT does not move, and CoT multiplies output tokens 3–10x to get there. Worse,
it fights constrained decoding: if the schema puts answer fields before any reasoning field, the
model is forced to commit before it has "thought."

**If a rationale is wanted for auditability, generate it after the answer, not before.**

### Constrained decoding: better on both axes, and the paper everyone cites is wrong

The widely-circulated claim that format restrictions degrade reasoning by 10–30% comes from
**"Let Me Speak Freely?"** ([arXiv:2408.02442](https://arxiv.org/abs/2408.02442), EMNLP 2024
Industry). The [dottxt rebuttal](https://blog.dottxt.ai/say-what-you-mean.html) shows its
"structured" arm was **naive JSON-mode prompting with no schema**, with mismatched prompts between
arms and an LLM used as the parser for the free-form arm — not a neutral referee. Rerun with
matched prompts and real constrained decoding, structured **matched or beat** free-form.

**JSONSchemaBench** ([arXiv:2501.10868](https://arxiv.org/abs/2501.10868)) settles it across
10,000 real schemas and 6 engines: constrained decoding **improves downstream quality by up to 4%
and speeds generation**. XGrammar ([arXiv:2411.15100](https://arxiv.org/abs/2411.15100)) reports
up to 100x lower per-token latency, so "grammars are slow" is no longer true either. The real
residual risk is a *coverage* gap — complex schemas that an engine silently under-constrains —
not a reasoning gap.

**So schema-enforced decoding is not a safety-for-quality trade here. It is better on both.**

### Self-critique: only with external ground truth, which we happen to have

**"Large Language Models Cannot Self-Correct Reasoning Yet"**
([arXiv:2310.01798](https://arxiv.org/abs/2310.01798), ICLR 2024): *intrinsic* self-correction —
a model critiquing its own output using only its own judgement — fails to improve accuracy and
sometimes degrades it. The TACL critical survey
([arXiv:2406.01297](https://arxiv.org/abs/2406.01297)) generalises it: self-correction works
reliably **only when reliable external feedback exists** — a checker, an interpreter, ground truth.
The bottleneck is feedback *generation*, not the correction.

Self-Refine's reported ~20% gain sits in the other category: subjective generation tasks where the
model's own taste is a legitimate signal. Extraction has an objectively correct answer, so it
falls on the negative side.

**This is why the reviewer in this system is the grounding gate and not a model.** A deterministic
substring check on the evidence span catches a hallucinated quote with certainty, costs nothing,
and cannot be talked out of its verdict. An LLM re-reading its own extraction is the discredited
pattern. Escalate to a second *differently-grounded* model call only for records the deterministic
check flags — routing, not critique.

### Debate: rejected, with numbers

Du et al. ([arXiv:2305.14325](https://arxiv.org/abs/2305.14325)) reported the original positive
result. The follow-ups reverse it:

- **"Talk Isn't Always Cheap"** ([arXiv:2509.05396](https://arxiv.org/html/2509.05396v1)) documents
  conformity and sycophancy — weaker models abandon correct answers to match the majority, and the
  group converges even when wrong.
- A 2026 cost analysis ([arXiv:2605.00914](https://arxiv.org/abs/2605.00914), preprint — treat the
  figures as preliminary) reports a **2.1–3.4x token multiplier** for accuracy "statistically
  comparable to, or worse than" non-communicative baselines. Its MMLU-Hard example: isolated
  self-correction **66.7% at 619 tokens**; debate **60.7% at 17,401 tokens** — worse accuracy at
  roughly 28x the spend.

### And ensembling similar models is close to worthless

This is the finding that most sharpens the "fan out by lens, not by volume" rule in §3:

- **Apple, "Nine Judges, Two Effective Votes"** — a panel of **9 frontier models from 7 different
  families** carries the information content of about **two independent votes**, and the single
  best judge matches or beats the whole panel.
- **"Correlated Errors in Large Language Models"**
  ([arXiv:2506.07962](https://arxiv.org/abs/2506.07962), ICML 2025) — models from the same family
  make correlated errors, and **the correlation increases as accuracy increases.** Better models
  fail on the same items.

So a majority vote among similar models is not cross-checking; it is one opinion counted several
times, with the appearance of confirmation. Spend that budget on a grounded verifier instead.

### Error compounding, which decides against long chains

If each step is 70% correct, a three-step chain is **~34%** correct. Multiplicative, not additive.
This is the strongest single argument against chaining agentic calls anywhere correctness matters
— and it is why the extraction path is one call plus a deterministic check, not a pipeline of
model calls each cleaning up after the last.

### Tool access on the extractor: no, and the framing is the useful part

Simon Willison's **lethal trifecta** — access to private data, exposure to untrusted content, and
an ability to exfiltrate — is only dangerous when all three are present. **Remove any one leg and
indirect prompt injection stops being exploitable**, regardless of how clever the injected text is.

A news document is untrusted content by definition. So the extractor is a pure *quarantined*
reader in the dual-LLM pattern: it reads untrusted text, emits a typed record, and has **no tools
at all**. Tools live only in the corroboration agent, and even there they are read/search only —
no write, no send — which breaks the trifecta for the agentic component too.

Documented agentic failure modes worth designing against: **cost runaway** from O(N²) context
accumulation as tool outputs pile into a growing message array ("a $0.05 task becomes a $5.00
infinite loop without a single error being thrown"), and repeating loops that show in traces as
identical spans with rising cost and no state change. Both need explicit step budgets and
progress detection — never trust the model to stop itself.

### The decision rule, stated plainly

Anthropic's [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
draws the line this document has been drawing: **workflows** are LLMs orchestrated through
predefined code paths; **agents** dynamically direct their own process. Use a workflow when the
number of steps is known in advance. Use an agent only when it genuinely cannot be.

Extraction has a fixed schema and a fixed step count — the textbook case for *not* making it
agentic. Corroboration has an unknown step count — the one place in this system where agency is
earned, and even there with a hard step and cost budget and an explicit stop condition.
