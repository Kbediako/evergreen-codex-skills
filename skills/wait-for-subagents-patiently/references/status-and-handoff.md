# Status And Handoff

## Use Precise Status Language

| Evidence | Report |
| --- | --- |
| Wait timed out | “No agent update arrived in this wait window.” |
| `list_agents` shows running | “The child is still running.” |
| Partial evidence would help | “I am asking for a concise checkpoint.” |
| Blocking hard decision point arrived | “I am using the available evidence to make the next authorized decision.” |
| Interrupt reports completed | “The child had completed by interrupt time.” |
| Completed status; final answer unavailable | “The child completed; its final answer has not yet been consumed.” |
| Final answer verified | “The child completed and I verified its result.” |

Avoid “stalled,” “hung,” “failed,” or “done” unless evidence supports that exact state.

## Give Checkpoint Updates

Use concise updates:

```text
No update arrived in this wait window. I am continuing parent-side work and will wait on the child mailbox when its result becomes blocking.
```

```text
The hard decision point is approaching and the child blocks the next step. I am requesting a checkpoint while time remains for the response and decision.
```

```text
I interrupted the child because its scope became obsolete. That does not classify the child as failed or stalled.
```

```text
I moved this child out of the critical path. That is a scheduling decision, not stall evidence.
```

## Reconcile For Handoff

Report the decision-relevant facts, without repeating an unchanged coordination log:

- child path and scope;
- verified lifecycle state;
- waits that timed out when materially relevant;
- checkpoint requests and responses;
- whether a final answer was consumed;
- parent verification performed;
- interruption or supersession reason;
- results intentionally omitted;
- still-running work;
- unresolved write ownership or known outstanding operations and consequential effects;
- resume or compaction reconciliation;
- duplicate spawns prevented.

Do not claim completion from status alone. Consume the final child answer and verify its important evidence before including the result.
