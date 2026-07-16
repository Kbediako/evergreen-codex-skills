---
name: challenge-assumptions
description: Falsify uncertain root-cause claims in ambiguous, repeated, disputed, or failed-repair investigations; do not use when current authoritative evidence already establishes a straightforward low-risk cause and one direct validation is sufficient. Use for conflicting evidence, user-observed contradictions, policy-, permission-, network-, auth-, dependency-, upstream-, or runtime-shaped errors, or before high-impact remediation or blaming another system without proof.
---

# Challenge Assumptions

## Overview

Use this skill to keep investigations evidence-led after a plausible explanation appears early. The goal is not endless skepticism; it is to prove or falsify the current explanation with the smallest safe checks that can change the next action or conclusion.

Treat any past incident as an example, not a template. Adapt the checks to the failing system's domain while preserving the same falsification discipline.

## Scale The Workflow

Match the ceremony to the uncertainty and consequence:

- **Micro:** For one low-risk claim that one probe is expected to decide, record the claim, the cheapest disproof, and the decision it would change. Run the probe; stop if it decides the claim. If it is inconclusive or exposes a material branch, switch to Full only for that unresolved branch. Do not manufacture a three-row ledger or broad matrix.
- **Full:** For ambiguous, persistent, high-impact, multi-layer, or conflicting failures, use the hypothesis ledger and differential boundary checks below.
- **Resume:** When the investigation and evidence boundary are unchanged, reuse the existing ledger and settled evidence. Update only changed facts. Do not reload, restate, or rerun the full workflow for a routine status question or a new turn.

Rebuild the ledger when the claim, scope, active runtime, authoritative source, or failure signature materially changes.

## Workflow

### 1. State The Claim

In Full mode, write the current best hypothesis before diagnostic or corrective action, unless the narrowest safe, authorized containment is needed first to limit ongoing harm; record the containment and any evidence it may disturb, then state the hypothesis. In Micro mode, record only the claim, cheapest disproof, and decision delta:

```text
Current best hypothesis: <claim>
Evidence for it: <observations>
Prediction: <distinct observation expected if the claim is true>
Missing proof: <what would make it true>
Cheapest disproof: <small check that could falsify it>
Decision delta: <what action or conclusion would change>
Confidence: low/medium/high
```

Do not present the claim to the user as fact until the missing proof is resolved.

Before a state-changing probe or repair that could erase or confound material evidence, capture the smallest feasible baseline or evidence snapshot. If immediate containment must take precedence, record the resulting loss of observability.

### 2. Establish Authority And Freshness

Before making a status, impact, or progress claim, identify the source authoritative for each underlying fact. For a causal claim, identify the authoritative observations and state the inference that connects them:

- Name the artifact, runtime state, metric, API, log, or user-observed repro that owns each observation; treat any diagnosis embedded in that source as another claim unless independently supported.
- Check its timestamp, version, scope, and current producer when drift is plausible.
- Label substitutes as proxy, stale, partial, or differently scoped instead of treating them as equivalent.
- Disambiguate similarly named counters, phases, gates, branches, environments, and success criteria before comparing them.
- Treat activity counts such as spawns, reviews, retries, files, or steps as activity, not goal progress, unless the goal explicitly measures them.

If a factual premise depends on a non-authoritative proxy, say so and probe the authoritative boundary when a safe, authorized probe with justified decision value is available. Otherwise constrain the claim and any next action to the proxy's known scope, uncertainty, and the reversibility and consequence of that action.

### 3. Build A Hypothesis Ledger

For the full workflow, track the materially plausible causes, usually two to four. Do not add or retain an entry solely to satisfy a count.

```text
Hypothesis | Evidence for | Evidence against | Falsifying check | Status
```

For environment, tool, UI, API, MCP, auth, runtime, CI, or deployment failures, consider these layers when each is plausible:

- One local configuration/process/cache hypothesis.
- One target-specific hypothesis.
- One upstream/service/policy hypothesis.

Do not replace an upstream bias with a local bias. Promote whichever hypothesis best predicts the current authoritative evidence.

### 4. Run Differential Probes

Prefer cheap checks that split the search space:

- Failing target vs a different known target.
- Real target vs minimal local probe.
- Metadata/read-only access vs the actual failing action.
- Disk config vs the running process environment.
- Active runtime version/hash/path vs configured or documented paths.
- Current handle/session vs fresh handle/session.
- User-reported working environment vs this machine's local state.

If a valid differential probe contradicts the initial hypothesis, pause and update the ledger before continuing.

Before each probe, determine—not necessarily narrate—the competing outcomes and which decision, confidence tier, safety boundary, or user-facing conclusion the result can change. Start with one to three high-information probes. Expand only when the result leaves a material branch unresolved; skip matrix items that cannot change the next action.

Treat a differential as falsifying only when the compared paths are materially comparable except for the factor under test, or when known confounders are explicitly accounted for. When outcomes are intermittent, delayed, rate-based, or stochastic, define the baseline and observation window and repeat only enough to distinguish a real effect from normal variation; do not treat one sample as decisive.

Treat absence of an expected observation as evidence against a hypothesis only when the observation source or probe had sufficient sensitivity, coverage, timing, and retention to detect it if present; otherwise record the result as inconclusive, not falsifying.

For tool, UI, API, browser, automation, deployment, or embedded-control failures that look like policy, permission, target denial, or upstream refusal, select the smallest applicable subset of these boundary checks before concluding the target is blocked:

- Fresh handle/session to the failing target.
- One unrelated comparable target, origin, account, project, tenant, job, endpoint, or fixture.
- A no-op, dry-run, empty, health-check, local, or minimal target that should not depend on the suspected external system, when safe.
- Metadata-only, read-only, or discovery access vs the actual failing action.
- Configured control path vs the active runtime/control path.

Examples: for browser failures, compare `about:blank`, an unrelated origin, loopback/local files, and DOM/action access; for API failures, compare health/read endpoints, another resource, dry-run behavior, credentials scope, and the active client/runtime.

If a valid minimal/no-op differential works while real targets fail, lower confidence only in hypotheses that predicted the minimal path would also fail under the tested conditions; do not infer a causal location from the simpler path's success alone. If unrelated targets exhibit comparable failures, lower confidence in a target-specific cause only when independent evidence shows that a common causal dependency or state accounts for them; identical or normalized output, or a shared failure mechanism alone, is non-diagnostic. Keep distinct target-specific, local-control, and shared external causes open until another valid differential or concrete artifact distinguishes them.

For local tool, plugin, browser, MCP, CLI, app-server, test runner, deployment helper, or runtime failures, consider these candidate checks early and run only those with a stated decision delta:

- Effective config that launches the tool.
- Running process command line and environment, if available.
- User or system environment values that the process may inherit.
- Existence of configured executable and cache paths.
- `--version`, `doctor`, or equivalent health command for the active executable when safe.

### 5. Treat Error Messages As Claims

An error message names a symptom, not necessarily the root cause.

Challenging a policy-shaped error means verifying whether the named policy is truly the root cause. It does not mean bypassing policy, safety, authentication, enterprise controls, site restrictions, or user-consent boundaries. Use supported diagnostics, benign alternate targets, local config/log inspection, and exact evidence. Stop and escalate if verification would require forbidden access or credentialed workarounds.

- If it says policy or enterprise block, verify the authoritative policy boundary; inspect local policy/config/env/log paths only when they can originate, cache, scope, or rewrite the result.
- If it says network or site block, verify the relevant network boundary and choose the smallest safe, scope-equivalent control that can distinguish a target-specific cause from a shared-path cause; do not assume a public or local target is comparable.
- If it says permission or admin, verify the effective principal, requested operation, resource scope, and applicable ownership, ACL, role, or policy boundary before recommending elevation.
- If it says missing dependency or unsupported version, verify the active component and version, plus only the package, runtime, cache, or config surface needed to establish what the failing consumer loaded.
- If a path that should not traverse the named policy boundary is independently shown to share a common causal dependency or state that accounts for both failures, demote the named-boundary hypothesis and promote that shared cause. Identical or normalized message text—or merely the same failure mechanism—does not establish a shared cause; keep distinct causes open. Promote a specific local-path cause only when an independent comparison or concrete local artifact or state separates it from other shared causes. Comparable failure across unrelated real targets alone does not distinguish local from shared external causes.

When evidence isolates the local control path, promote the best-supported cause within that path as the leading hypothesis. Conclude it only when authoritative observations support a valid causal inference with confidence proportionate to the next action. A behavior-changing comparison or repair is strong confirmation only when it is a valid discriminating test; a broad, bundled, or uncontrolled change may validate recovery without identifying which changed factor was causal. Do not require an intervention when it is unsafe or unavailable and the causal path is otherwise directly established.

### 6. Search The Exact Boundary

When an exact error string, status code, symbol, or failing path can change the next action, search first at its authoritative producer or boundary, then only in relevant local, deployed, source, configuration, or runtime surfaces that can originate or transform it.

Prefer exact-string and path-based searches over broad guessing. Do not search a fixed local checklist when those surfaces cannot affect the error.

### 7. Validate Repairs Against The Active Runtime

After any repair, verify the affected active system or control boundary rather than trusting the declared or stored change:

- Confirm that the relevant active consumer or boundary and its effective identity, version, configuration, or state match the intended repair; inspect only attributes applicable to that system.
- If activation requires it, reload, restart, or reconcile only the narrowest affected component, when safe and authorized.
- Rerun the original failing core action only when it is safe and repeatable without unacceptable side effects; otherwise use the closest safe equivalent, canary, simulation, or read-only validation that exercises the repaired path.
- Rerun a differential probe that previously separated good from bad behavior only when one exists, is safe to repeat, and can still change the conclusion.

If the selected safe validation still fails or is inconclusive after an attempted repair, run a failed-repair audit before trying the same class of fix again:

- Intended change: what was intended to change and how its effective state was independently confirmed.
- Intended recipient or boundary: the component, actor, process, runtime, session, or control path expected to reflect the change.
- Effective-change evidence: authoritative evidence showing whether and when the change reached or affected that recipient or boundary.
- Behavior check: the selected safe validation, plus the next smallest differential probe only when it distinguishes an unresolved branch.

Interpret the audit before continuing:

- If the change did not reach or affect the intended recipient or boundary, investigate precedence, activation, propagation, reconciliation, lifecycle, or the delivery/control path before changing more state.
- If the change reached or affected the intended recipient or boundary, any required activation or propagation window has elapsed, and a valid behavior check remains materially identical, demote the exact repair mechanism. Demote the causal hypothesis or move to another ledger entry only if that repair was a valid discriminating test of it.
- If the failure signature changed, update the repro, evidence, and hypothesis ledger before applying another fix.

Do not report a repair as complete until the original failure path or a demonstrably scope-equivalent surrogate safely passes and any material safety or regression guardrails affected by the repair have been checked proportionately. If the primary path, an affected guardrail, or both cannot be validated, report the validation scope and residual uncertainty instead of claiming full confirmation.

### 8. Persist With Guardrails

Keep moving only while another safe, authorized probe can change the action, confidence tier, safety boundary, or conclusion and its expected decision value justifies its cost, delay, disruption, and residual risk. Before adding a probe, name that decision delta. Stop when one of these is true:

- The root cause is verified and a narrow fix or escalation is clear.
- The remaining checks cannot proceed without user approval, credentials or authorization not currently available, destructive or forbidden changes, or external state that cannot yet be safely observed or controlled.
- Enough evidence, using meaningfully independent provenance or failure paths where needed—not merely different interfaces or views of the same source—identifies the concrete blocker with confidence proportionate to the consequence and reversibility of the next action, and no remaining safe probe can materially change that decision. Repeating the same failing action, API call, tab handle, or error-producing path does not count as independent evidence.
- Remaining checks cannot change the next action or materially improve confidence in it, or their expected decision value does not justify their cost, delay, disruption, or risk.

When stopped, report the active hypothesis, evidence, rejected hypotheses, and the next missing fact.

## User Pushback Protocol

Treat new, specific user-observed facts in pushback as evidence; treat the user's causal explanation as a hypothesis.

Do this immediately:

1. Restate the observed fact separately from the user's explanation.
2. Lower confidence in each premise that conflicts with it; do not discard unrelated verified facts.
3. Check whether the disputed premise relied on authoritative, current, scope-equivalent evidence.
4. If the observation opens a material branch not already tested, add the cheapest safe, authorized differential probe that distinguishes it from the current theory and whose expected decision value justifies its cost, delay, disruption, and residual risk.
5. Run that probe before repeating the earlier conclusion. If no such probe is justified or available, state the unresolved branch and constrain the conclusion and next action to the evidence that remains.
6. Correct affected claims individually before giving new steering. Treat the user's theory as a hypothesis to test, not as evidence or automatically true.

## Output Shape

For a micro investigation, report the conclusion, decisive probe, and decision delta. For a full investigation, include a compact ledger in progress updates or final answers:

```text
Verified observations:
- <facts supported by authoritative, current, scope-equivalent measurements, artifacts, runtime state, tests, logs, or user repros>

Causal inference:
- <current explanation, supporting observations, and confidence>

Rejected:
- <hypotheses tested and falsified>

Still possible:
- <hypotheses not yet ruled out>

Next:
- <narrow fix, validation, or concrete blocker>

Decision delta:
- Before probe: <likely action or conclusion>
- After probe: <changed or confirmed action or conclusion>
```

Do not expose internal ceremony when it would make a simple answer harder to use.

## Anti-Patterns

- Do not stop at "metadata is visible but action is blocked" without testing where the block begins when a safe, authorized probe with a decision delta exists and its expected decision value justifies its cost, delay, disruption, and residual risk; otherwise report the boundary as unverified and state the blocker.
- Do not run a full ledger or boundary matrix when one cheap probe can decide a low-risk claim.
- Do not rebuild a settled ledger on every turn or routine status check; reuse it until the evidence boundary changes.
- Do not use stale, proxy, or differently scoped metrics as authoritative evidence without labeling and validating them.
- Do not equate a policy-shaped error with a real policy until the authoritative policy boundary has been checked; do not require local policy inputs when they cannot affect that boundary.
- Do not overcorrect toward a local root cause merely because upstream explanations are being challenged.
- Do not recommend privilege elevation or broad or disruptive remedies such as reinstalling, cache deletion, or full restart unless authoritative evidence shows they are necessary at the failing boundary and no narrower supported remedy is sufficient.
- Do not treat user pushback as merely conversational; preserve new observed facts as evidence and treat any causal theory they introduce as a hypothesis subject to the materiality, safety, authorization, and decision-value guardrails above.
- Do not repeat or broaden a failed repair until you have established whether and how the intended change reached or affected the active failure path and why the selected validation still fails or remains inconclusive.
- Do not bypass policy or safety controls to prove a point. Diagnose through supported surfaces.
