# Budgets And Stall Evidence

Use these defaults only when neither the user nor a task-domain skill provides a patience policy.

## Record A Waiting Budget

Record:

- start time;
- task complexity: small, normal, or deep;
- expected checkpoint;
- hard decision point;
- whether the child blocks the parent's next action.

| Task | Checkpoint | Hard decision |
| --- | --- | --- |
| Small lookup or single-file check | 2-3 minutes | 5-8 minutes |
| Normal code search, review, or multi-file audit | 5-10 minutes | 15-20 minutes |
| Deep review, browser work, JSONL audit, or large parsing | 10-20 minutes | 30-45 minutes |

Override these defaults for explicit long-running instructions, ChatGPT Pro review, domain-specific research, browser finalization, useful incoming evidence, or a task-specific contract. Treat elapsed time as scheduling input, never as stall proof.

At a blocking hard decision point:

1. Request a hard checkpoint.
2. Wait one more reasonable window.
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
