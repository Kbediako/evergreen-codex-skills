---
name: challenge-assumptions
description: Falsify uncertain root-cause claims in ambiguous, repeated, disputed, or failed-repair investigations; do not use when current authoritative evidence already establishes a straightforward cause and one direct, safe, low-risk, non-state-changing validation is sufficient. Use for conflicting evidence, user-observed contradictions, policy-, permission-, network-, auth-, dependency-, upstream-, or runtime-shaped errors, or before a state-changing diagnostic or any high-impact diagnostic or remediation, or blaming another system without proof.
---

# Challenge Assumptions

Keep investigations evidence-led after a plausible explanation appears. Prove or falsify the current explanation with the smallest safe checks that can change the next action; do not turn healthy skepticism into ceremony.

Treat past incidents as examples, not templates. Adapt the probes to the domain.

## Choose The Depth

- **Micro:** For one low-risk claim that one probe should decide, record the claim, cheapest disproof, and decision delta. Stop if the probe decides it; expand only the unresolved branch.
- **Full:** For ambiguous, persistent, high-impact, multi-layer, or conflicting failures, use a compact hypothesis ledger and differential probes.
- **Resume:** Reuse settled evidence and the existing ledger while the claim, scope, active system, authoritative source, and failure signature remain unchanged. Update only changed facts.

## Load Conditional Guidance

Read only the references required by the case:

- For Full investigations, disputed evidence, policy-shaped errors, or boundary isolation, read [evidence-and-probes.md](references/evidence-and-probes.md) before choosing probes.
- Before any state-changing diagnostic, containment, or repair, and whenever a repair fails or is inconclusive, read [repair-validation.md](references/repair-validation.md) before acting or declaring completion.
- When user pushback changes the evidence, or a Full investigation needs a durable result, read [pushback-and-reporting.md](references/pushback-and-reporting.md).

## Core Workflow

### 1. Frame The Claim

Separate authoritative observations from the causal inference. In Full mode, record:

```text
Hypothesis: <current explanation>
Observations: <facts and authoritative sources>
Prediction: <distinct result expected if true>
Cheapest disproof: <small safe check>
Decision delta: <action or conclusion that would change>
Confidence: low/medium/high
```

Do not present the hypothesis as fact. If urgent containment must precede diagnosis, use the narrowest safe, authorized containment and record evidence or observability it disturbs.

### 2. Establish Evidence Authority

For each material fact, identify its authoritative producer, current scope, timestamp or version, and the active system that consumed it. Label proxy, stale, partial, or differently scoped evidence instead of treating it as equivalent.

Treat a diagnosis embedded in a log, API, UI, or error message as a claim unless independent observations support it. Treat activity counts as activity, not progress, unless the goal measures them.

### 3. Keep Real Alternatives Open

In Full mode, track only materially plausible hypotheses, usually two to four:

```text
Hypothesis | Evidence for | Evidence against | Falsifying check | Status
```

Do not replace upstream bias with local bias. Promote the explanation that best predicts current authoritative evidence. Identical text, a shared handler, or a shared failure mechanism does not by itself establish a shared cause.

### 4. Choose Decision-Changing Probes

Before each probe, determine the competing outcomes and which action, confidence tier, safety boundary, or conclusion they change. Run one to three high-information probes first; expand only while a material branch remains.

Use a result as falsifying evidence only when the probe validly tests the hypothesis. Account for comparability, confounders, sensitivity, coverage, timing, retention, and stochastic variation as applicable.

Run a probe only when it is safe, authorized, and its expected decision value justifies its cost, delay, disruption, and residual risk.

### 5. Update, Repair, Or Stop

When evidence contradicts a premise, update the ledger before repeating the conclusion. A behavior-changing comparison confirms a cause only when it is a valid discriminating test; a broad, bundled, or uncontrolled change may prove recovery without identifying the cause.

Stop when:

- The cause is verified and a narrow fix or escalation is clear.
- Required approval or authorization is unavailable, or the remaining checks are destructive, forbidden, or depend on external state that cannot yet be safely observed or controlled.
- Confidence is proportionate to the consequence and reversibility of the next action, and no worthwhile safe probe can materially change it.
- Further checks cannot change the next action or materially improve confidence, or their decision value does not justify their cost or risk.

When stopping under uncertainty, state the leading inference, verified observations, rejected and unresolved alternatives, next action, and missing fact.

## Non-Negotiable Guardrails

- Do not bypass policy, safety, authentication, enterprise controls, or user-consent boundaries to prove a point.
- Do not infer a causal location from a simpler path's success; lower confidence only in hypotheses that predicted that path would fail under the tested conditions.
- Do not treat absence of evidence as falsifying unless the observation path could reliably detect the expected event.
- Do not recommend privilege elevation or broad disruptive remedies unless authoritative evidence makes them necessary and no narrower supported remedy is sufficient.
- Do not repeat or broaden a failed repair until you establish whether and how the intended change reached the failure path and why valid testing still fails or remains inconclusive.
- Do not claim repair completion until the original path or a demonstrably scope-equivalent surrogate passes and affected safety or regression guardrails have been checked proportionately.
- Keep internal ceremony out of user-facing answers when a simpler explanation is sufficient.
