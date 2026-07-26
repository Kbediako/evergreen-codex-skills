---
name: wait-for-subagents-patiently
description: Reconcile and wait for native Codex children when a child is quiet, appears hung, exceeds an estimate, or a wait window times out. Use before calling a child stalled, interrupting it, replacing it, or handing off without its final answer.
---

# Wait For Subagents Patiently

## Load The Contract

Load [native-subagents-first](../native-subagents-first/SKILL.md) for lifecycle, model, scope, budget, resume, and direct-tool rules. Apply this skill only to patience, evidence, checkpoint, interruption, and handoff decisions.

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
2. Poll again when the answer is not yet required.
3. Ask for a soft checkpoint when partial evidence would help.
4. Ask for a hard checkpoint before interrupting for elapsed-time or budget reasons.
5. Wait one reasonable window after the hard checkpoint.
6. Consume and verify any final answer before deciding the next action.

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
