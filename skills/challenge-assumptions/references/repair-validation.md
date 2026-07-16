# Repair Validation

Read this reference before a state-changing diagnostic, containment, or repair, and whenever a repair fails or remains inconclusive.

## Preserve Evidence Before Mutation

Before changing state in a way that could erase or confound material evidence, capture the smallest feasible baseline or evidence snapshot. If immediate containment must take precedence, record the resulting loss of observability.

## Verify The Effective Change

After applying a state-changing diagnostic, containment, or repair, verify the affected active system or control boundary rather than trusting the declared or stored change:

- Confirm the relevant active recipient or boundary and applicable identity, version, configuration, or state.
- If activation requires it, reload, restart, or reconcile only the narrowest affected component when safe and authorized.
- Rerun the original action only when safe and repeatable without unacceptable side effects. Otherwise use the closest safe canary, simulation, read-only validation, or demonstrably scope-equivalent surrogate.
- Repeat a prior differential only when it remains valid, safe, and capable of changing the conclusion.

## Audit A Failed Or Inconclusive Repair

Before repeating the same class of fix, record:

```text
Intended change: <what should have changed and how effective state was confirmed>
Recipient or boundary: <where the change should appear>
Effective-change evidence: <whether and when it reached or affected that boundary>
Behavior check: <safe validation and any decision-changing differential>
```

Interpret the audit:

- If the change did not reach or affect the intended boundary, investigate precedence, activation, propagation, reconciliation, lifecycle, or the delivery/control path before changing more state.
- If it reached the boundary, the required propagation window elapsed, and a valid behavior check remained materially identical, demote the repair mechanism. Demote the causal hypothesis only when that repair was a valid discriminating test of it.
- If the failure signature changed, update the reproduction, evidence, and ledger before another fix.
- If results are partial or probabilistic, define the intended effect, baseline, observation window, and sufficient samples before judging the repair.

## Declare Completion Conservatively

Report a repair as complete only when:

- The original failure path or a demonstrably scope-equivalent surrogate safely passes.
- Material safety, access-scope, integrity, compatibility, and adjacent-function regression guardrails affected by the change have been checked proportionately.
- Effective active state, not merely the stored change, matches the intended repair.

If the primary path or an affected guardrail cannot be validated, state the validation scope and residual uncertainty rather than claiming full confirmation.
