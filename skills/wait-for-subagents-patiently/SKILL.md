---
name: wait-for-subagents-patiently
description: Reconcile and wait for native Codex children when a child is quiet, appears hung, exceeds an estimate, or a wait window times out. Use before calling a child stalled, interrupting it, replacing it, or handing off without its final answer.
---

# Wait For Subagents Patiently

## Load The Contract

If it is not already active, load [native-subagents-first](../native-subagents-first/SKILL.md) for lifecycle, model, scope, budget, resume, and direct-tool rules. Never recursively reload it. Apply this skill only to patience, evidence, checkpoint, interruption, and handoff decisions.

Use [long-poll-wait](../long-poll-wait/SKILL.md) for external jobs, processes, CI, training, or remote monitors.

## Treat Timeout As Nonterminal

- Treat a `wait_agent` timeout as "no update arrived in this wait window."
- Do not infer failure, a hang, or lack of progress from timeout alone.
- Treat `running` as a lifecycle state, not task-result evidence.
- Keep `quiet`, `late`, `over budget`, `interrupted`, `completed`, and `stalled` distinct.
- Verify important child claims in the parent before using them.

## Reconcile Before Acting

After steering, resume, compaction, interruption, or a new user message:

1. Call `list_agents`.
2. Match existing child paths to the current scope.
3. Consume queued or final child messages.
4. Inspect expected artifacts or rollout evidence when status is incomplete.
5. Reuse the child through `wait_agent` or an in-brief `send_message`. Use `followup_task` only for a distinct continuation or scope expansion; it consumes a run and needs the remaining-budget and progress-delta gates in `native-subagents-first`.
6. Replace a child only when it is obsolete, irrecoverable, outside scope, or beyond a hard decision point after checkpointing; replacements consume a child run.

Do not create renamed duplicates such as `_2`, `retry`, or `fresh` without proving the original cannot serve the scope.

## Wait Deliberately

1. Continue non-overlapping parent work while the child runs.
2. When the result becomes blocking, call `wait_agent`; this is a mailbox wait, not a status poll.
3. On timeout, continue useful work or enter another bounded mailbox wait only while the result remains blocking. Do not inspect `list_agents`, send a checkpoint, or narrate unchanged state solely because a timer expired.
4. Ask for a soft checkpoint when partial evidence would materially help.
5. Ask for a hard checkpoint before interrupting for a concrete hard-decision reason, then wait one reasonable mailbox window.
6. Consume and verify any final answer before deciding the next action.

Use the longest wait window compatible with the host's user-update rules and the task's next decision point. Never replace the mailbox wait with sleeps, shell loops, or repeated lifecycle snapshots.

Use:

```text
Please return a brief checkpoint from evidence gathered so far if convenient, and continue the original task while useful progress remains.
```

Before interruption, use:

```text
Please stop starting new work and return a concise checkpoint from evidence already gathered: outcome, changes, validation, findings, evidence, and blockers.
```

## Override Generic Time Defaults

Let explicit user instructions and task-domain patience rules override generic elapsed-time defaults. Allow long-running reviews, ChatGPT Pro consultations, browser-heavy research, remote analysis, and domain workflows to continue while useful evidence or finalization may still arrive.

Never force a Pro or long-running reviewer to answer early merely because a generic checkpoint estimate elapsed. Checkpoint or interrupt only for a concrete authority, scope, safety, resource, obsolescence, or hard-decision reason.

Read [budgets-and-stall-evidence.md](references/budgets-and-stall-evidence.md) when setting default checkpoints, judging over-budget work, or assessing a possible stall.

## Interrupt Carefully

Interrupt only for a concrete reason:

- the user asks to stop;
- the scope became obsolete;
- the child violates scope or permissions;
- scarce resources or external side effects require intervention;
- a blocking hard decision point passed after checkpointing.

Inspect the interrupt result immediately. If `previous_status` contains a completed answer, classify the child as completed at interrupt time, consume that answer, and do not call it stalled.

## Handoff

Read [status-and-handoff.md](references/status-and-handoff.md) for precise status language and handoff examples.

Before handoff:

- report verified lifecycle state for every relevant child;
- identify final answers consumed and parent checks performed;
- identify omitted results and still-running work;
- report interruptions and their concrete reasons;
- report any duplicate spawn prevented during reconciliation.
