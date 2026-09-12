---
name: native-subagents-first
description: Coordinate native Codex subagents for requested parallel work or independent execution and review scopes. Use for ownership, worker selection, and lifecycle management.
---

# Native subagents first

The primary agent owns the whole outcome. Delegate independently useful work, integrate returned evidence, and complete the original task. Stay solo when separation adds more coordination cost than value, unless an active delegate-only instruction requires delegation.

Use the direct collaboration tools exposed by the current runtime. The suite uses `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, `interrupt_agent`, and `list_agents`; verify availability rather than inventing tool aliases or a close step.

## Scope and launch

Define the outcome, observable acceptance criteria, exact workspaces, and authorization. Reconcile existing children with `list_agents` before launching work. Give coupled changes and their validation to one owner; directory count is not a reason to split them.

Use one stable milestone and cumulative child-run cap, preserved across resumes and steering. Each `spawn_agent` or `followup_task` consumes a run at any depth, including failed calls, retries, and replacements. Reserve nested runs before authorizing them. Fanout cannot exceed independent scopes, available slots, or remaining unreserved runs.

Before the first launch, read [briefs and ledger](references/briefs-and-ledger.md) for run accounting, progress gates, and compact briefs. Apply its detailed baseline procedure only to advisory read-only scopes. Record a relevant baseline for writes without inventorying unrelated trees.

Give workers exact ownership, task-local constraints, required evidence, and a stopping condition. Writers must preserve others' changes in the shared workspace. Leaf agents do not spawn unless granted a distinct scope and reserved budget. Use tool fields for roles and history, not pseudo-markers in prompts.

For a read-only assignment, read [read-only boundaries](references/read-only-boundaries.md). A prompt alone is not enforcement. Hard boundaries require verified isolation from consequential mutations; otherwise keep that work with an authorized parent. Best-effort read-only work requires bounded before/after detection.

## Select the worker

This suite specializes in GPT-6 Astra. Read [Astra routing](references/astra-routing.md) when selecting effort, a custom role, or context inheritance. Use a capable role proportionate to the uncertainty. Treat model and runtime labels as version-sensitive, and follow higher-priority model choices.

Prefer a fresh brief for a focused assignment; carry bounded history only when it supplies needed decisions. A full-history fork inherits the parent's model and effort and cannot be combined with overrides.

## Coordinate and integrate

Continue useful non-overlapping parent work while children run.

- `send_message` corrects an existing brief or transfers required evidence. Do not hide scope expansion in a message.
- `followup_task` starts a counted continuation or expanded task on an existing child.
- `wait_agent` waits for mailbox updates when the next action needs a child result. A timeout ends the wait window, not the task.
- `list_agents` supports reconciliation and lifecycle decisions, not timer-driven status checks.

Use the longest supported mailbox wait compatible with host responsiveness and the next decision point. Consume the actual update before treating a result as available.

Before a later launch batch, record a new parent-verified result or decision from the prior batch and check remaining budget under [briefs and ledger](references/briefs-and-ledger.md). Do not reset the cap by renaming milestones. If another run is not justified, consolidate or complete remaining authorized work in the parent only when the acceptance criteria permit it. Independent-review and controlled-trial requirements still apply, as do active delegate-only rules.

If evidence contradicts the assigned mechanism, the worker reports it and stays within scope. The parent resolves the direction within existing authority. Seek user input only for missing essential decisions or new authority.

## Resume, review, and finish

After steering, compaction, or resume, reconcile existing children, messages, and artifacts before replacing or duplicating work. Load [patient waiting](../wait-for-subagents-patiently/SKILL.md) for quiet children, deadlines, stalls, or intervention; do not recursively reload it. Domain patience rules, including not forcing Pro to answer, take precedence over estimates.

Before overlapping takeover, establish that the previous writer and its launched operations have stopped or are isolated. An interrupt does not imply rollback. An explicit stop or urgent safety boundary takes precedence over checkpoint requests.

Review a stable candidate when independent evidence is required or can resolve a named uncertainty. Stop repeated reviews that produce no changed implementation or evidence. After a failed repair wave, diagnose the failure before assigning equivalent fixes.

Consume required final answers and verify material claims against current artifacts. Reuse valid scoped evidence; rerun checks when changes or unresolved integration risks invalidate it. Complete affected and required project checks without adding testing merely to fill a checklist.

Report `done`, `partial`, or `blocked` with the integrated outcome, validation, missing evidence, and relevant lifecycle or ownership facts. Passing checkpoints do not replace the user's acceptance criteria or create approval gates.
