# Budgets And Stall Evidence

Elapsed time schedules work; it does not diagnose the child.

## Record A Waiting Budget

Record:

- start time;
- task complexity: small, normal, or deep;
- the next parent decision that actually needs the result;
- any user deadline, external expiry, scarce resource, or safety boundary;
- a checkpoint condition and hard decision point derived from those facts;
- the host's maximum practical blocking wait;
- whether the child blocks the parent's next action.

Do not invent generic minute tables or timer-driven status cadence. If no hard decision fact exists, keep the child off the critical path and use its mailbox only when its result becomes necessary. Explicit long-running instructions, ChatGPT Pro review, browser finalization, and domain patience rules remain authoritative.

At a blocking hard decision point:

1. Request a hard checkpoint.
2. Enter one reasonable mailbox wait.
3. Consume available final or checkpoint evidence.
4. Continue waiting, interrupt, supersede, or proceed without the child based on scope and risk.
5. Report the scheduling decision without inventing a stall.

Leave a read-only, non-side-effecting, non-blocking child running only when the active task can safely retain it. Reconcile it before any later duplicate spawn.

## Classify Evidence

Treat these as insufficient stall evidence:

- one or more wait timeouts;
- a `running` status;
- sparse or null last-message fields;
- elapsed time alone;
- parent impatience;
- an exceeded estimate without a stated hard decision policy.

Treat these as intervention facts, not automatic stall proof:

- terminal, failed, cancelled, interrupted, or unavailable status;
- a checkpoint that reports a blocker;
- out-of-scope work, duplicate work, or unauthorized mutation;
- scarce-resource or external-side-effect consumption;
- artifact, transcript, process, log, or repo evidence that contradicts expected progress;
- no response after a hard checkpoint and expiry of a blocking hard decision point.

Call a child stalled only when at least two independent signals show lack of progress rather than quiet execution, completion, cancellation, obsolescence, or parent interruption. State the signals.

## Prefer Exact Classifications

Use:

- `quiet/running` when no update arrived but status remains active;
- `over budget` when the stated estimate or decision point elapsed;
- `obsolete` when the parent no longer needs the work;
- `timeboxed out` when the result leaves the critical path;
- `completed-on-interrupt` when the interrupt response contains a completed result;
- `stalled` only with the evidence threshold above.
