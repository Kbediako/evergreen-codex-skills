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
5. For a running child, use an in-brief `send_message` or wait when its result is required. For an idle or interrupted child that needs to execute more work, use `followup_task`; a message or mailbox wait does not restart it. Resuming unfinished work is a counted continuation even when the objective is unchanged, and requires the remaining-budget and progress-delta gates in `native-subagents-first`. Recover an already-completed answer without starting another run solely to retrieve it.
6. Replace a child only when it is obsolete, irrecoverable, outside scope, or beyond a hard decision point under the checkpoint and urgency rules below; replacements consume a child run.

Do not create renamed duplicates such as `_2`, `retry`, or `fresh` without proving the original cannot serve the scope.

If another child run is not permitted, consolidate or perform remaining work in the parent where authorized and compatible with the acceptance criteria, or report the blocker. Before overlapping write work, apply the ownership-transfer rule under **Interrupt Carefully**.

## Wait Deliberately

1. Continue non-overlapping parent work while the child runs.
2. When the result becomes blocking, call `wait_agent`; this is a mailbox wait, not a status poll.
3. On timeout, continue useful work or enter another bounded mailbox wait only while the result remains blocking. Do not inspect `list_agents`, send a checkpoint, or narrate unchanged state solely because a timer expired.
4. Ask for a soft checkpoint when partial evidence would materially help.
5. Before a non-urgent scheduling interruption, request a hard checkpoint early enough for the response and decision. Bound the mailbox window by the remaining deadline and resource budget; skip the wait when no supported window fits. Apply the urgent-stop exception under **Interrupt Carefully**.
6. Consume and verify any final answer before deciding the next action.

Use the longest wait window compatible with the host's user-update rules and the task's next decision point. Never replace the mailbox wait with sleeps, shell loops, or repeated lifecycle snapshots.

A mailbox wake may concern any child or new user input. Consume the actual update before treating a required result as available; a wake summary is not the final answer.

Use:

```text
Please return a brief checkpoint from evidence gathered so far if convenient, and continue the original task while useful progress remains.
```

For a non-urgent checkpoint before scheduling interruption, use:

```text
Please stop starting new work and return a concise checkpoint from evidence already gathered: outcome, changes, validation, findings, evidence, and blockers.
```

## Override Generic Time Defaults

Let explicit user instructions and task-domain patience rules override generic elapsed-time defaults. Allow long-running reviews, ChatGPT Pro consultations, browser-heavy research, remote analysis, and domain workflows to continue while useful evidence or finalization may still arrive.

Never force a Pro or long-running reviewer to answer early merely because a generic checkpoint estimate elapsed. Use a hard checkpoint or interruption only for a concrete authority, scope, safety, resource, obsolescence, or hard-decision reason. A soft checkpoint may request useful partial evidence without ending the original work.

Read [budgets-and-stall-evidence.md](references/budgets-and-stall-evidence.md) when setting default checkpoints, judging over-budget work, or assessing a possible stall.

## Interrupt Carefully

Interrupt only for a concrete reason:

- the user asks to stop;
- the scope became obsolete;
- the child violates scope or permissions;
- scarce resources or external side effects require intervention;
- a blocking hard decision point passed, with prior checkpointing only when the real boundary allowed it.

Act promptly on an explicit user stop or an urgent safety, authorization, resource, or consequential-side-effect boundary; do not delay the necessary interruption to request or await a checkpoint. Reconcile afterward. Ordinary lateness or a generic elapsed-time estimate does not create this exception.

Inspect the interrupt result immediately. If the returned previous status indicates completion, classify the child as completed by interrupt time, even if the final answer is delivered separately. Recover and consume the actual final answer before using the result; until then, report completion with the final answer not yet consumed. Do not call it stalled or restart it merely because the answer was not embedded in the response.

Interruption does not imply rollback or cancellation of already-launched operations. Before the parent or a replacement takes overlapping write ownership, reconcile affected paths and retained changes, and establish that the previous writer and its known outstanding operations have stopped writing that scope or are isolated from it. Establish one current owner; unresolved writers or consequential effects block overlapping takeover. Observe or stop underlying operations only through their exact identities and existing authorization, preserving unrelated work.

## Handoff

Read [status-and-handoff.md](references/status-and-handoff.md) for precise status language and handoff examples.

Before handoff:

- report verified lifecycle state for every relevant child;
- identify final answers consumed and parent checks performed;
- identify omitted results and still-running work;
- report interruptions and their concrete reasons;
- report any duplicate spawn prevented during reconciliation.
