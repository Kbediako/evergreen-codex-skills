---
name: wait-for-subagents-patiently
description: Wait for quiet native Codex children and reconcile their state before declaring a stall, interrupting, replacing, or handing off without a result.
---

# Wait for subagents patiently

Use this for native children. External jobs use [long-poll-wait](../long-poll-wait/SKILL.md); app tasks use their own event-wait tool. Load [native-subagents-first](../native-subagents-first/SKILL.md) for native lifecycle and run accounting unless already active. Never recursively reload it.

## Wait on evidence

A `wait_agent` timeout means no update arrived in that window. It does not prove failure, a hang, or lack of progress. A `running` or `completed` status describes lifecycle; the actual answer and verified artifacts establish the result.

Continue independent parent work while the child runs. When its result blocks the next action, use `wait_agent` with the longest supported window compatible with host responsiveness and the next decision point. Do not replace mailbox waiting with sleeps or repeated lifecycle snapshots. Consume the actual mailbox update; a wake may concern another child or user input.

Ask for a checkpoint when partial evidence can change a decision. Do not request one, inspect `list_agents`, or narrate unchanged state solely because a timer expired. Let explicit domain patience rules govern long-running work. Never force Pro to answer early because an estimate elapsed.

## Reconcile existing work

After steering, resume, compaction, or interruption, use `list_agents` to match children to the current scope, consume queued or final messages, and inspect expected artifacts when status is incomplete.

Use `send_message` for an in-scope correction to a running child. Use `followup_task` for authorized execution by an idle or interrupted child; messages and waits do not restart it. Count that continuation under the native-agent budget. Recover a completed answer without starting another run solely to retrieve it.

Replace only when the original is obsolete, irrecoverable, outside scope, or past a real hard decision point. Reconcile first so renamed retries do not duplicate work.

## Decide whether to intervene

Read [budgets and stall evidence](references/budgets-and-stall-evidence.md) when a deadline, resource boundary, or possible stall affects the decision. Elapsed time alone does not establish a stall. A missing required result stays an acceptance gap even when observation ends.

Read [interruption and ownership](references/interruption-and-ownership.md) before a planned interruption or overlapping takeover. Request a checkpoint in advance only when the real deadline allows a response window. Act promptly on an explicit user stop or urgent safety, permission, resource, or consequential-side-effect boundary; reconcile afterward.

Interruption does not roll back edits or cancel launched operations. Establish that prior writers and known outstanding operations have stopped or are isolated before assigning overlapping write ownership. If the interrupt result says the child had completed, recover its answer instead of calling it stalled.

## Handoff

Report verified results, parent checks, missing answers, still-running work, intervention reasons, and unresolved ownership. Use [status and handoff](references/status-and-handoff.md) when precise lifecycle wording or a resumable handoff is needed. Do not turn status or activity into completion evidence.
