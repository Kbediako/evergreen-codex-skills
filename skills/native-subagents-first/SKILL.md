---
name: native-subagents-first
description: Coordinate bounded native Multi-Agent V2 work when the user asks for subagents, parallel agents, multi-agent implementation or review, or when an active native-agent workflow has genuinely independent streams. Use for GPT-6 Astra role selection, context inheritance, ownership, fanout, progress gates, and parent synthesis.
---

# Native Subagents First

## Operating Contract

Keep the primary agent accountable for the whole outcome. Delegate independent evidence or execution, stay available to the user, integrate child results, and verify the final state.

Use only the direct V2 tools exposed in the current task: `spawn_agent`, `send_message`, `followup_task`, `wait_agent`, `interrupt_agent`, and `list_agents`. Do not look for a close step.

Exact model labels, native-agent versions, direct tool names, and rollout fields are version-sensitive suite defaults; verify them against the active Codex runtime.

Stay solo when the work is tiny, sequential, tightly coupled, or cheaper to verify directly. A separate context must earn its coordination and token cost.

## Start A Milestone

1. Define the objective and 3-6 acceptance criteria.
2. Inventory the exact paths, authority boundary, validation commands, and current agent state.
3. Call `list_agents`; reconcile matching active and completed work before authorizing any child run.
4. Split only dependency-light scopes with independently useful evidence or disjoint write ownership.
5. Route by coupled outcomes and interfaces, not directory count. When several modules jointly determine one acceptance criterion, give one sequential owner the diagnosis, coordinated edits, and validation.
6. Declare a stable milestone ID, one cumulative child-run cap, and a terminal synthesis point.
7. Compute `fanout = min(independent scopes, remaining child-run budget, available child slots)`. Queue excess scopes.
8. Capture a bounded pre-work baseline for every read-only or write scope.

A child run is one task started by `spawn_agent` or `followup_task` at any depth, including a retry, replacement, or authorized nested run. Debit it when the tool is called even if the call fails, is interrupted, or is superseded.

Do not rename or subdivide a milestone to reset its cap. Preserve its ID, initial cap, used count, nested reservations, remaining budget, and latest parent progress delta across resumes, steering, compaction, and automatic continuation.

## Route GPT-6 Astra

Use GPT-6 Astra only. Read [references/astra-routing.md](references/astra-routing.md) before choosing effort, a custom role, or inherited context.

| Role | Effort | Default use |
| --- | --- | --- |
| Scout | `medium` | Narrow read-only lookup, path trace, relevant tests |
| Worker | `high` | Scoped implementation, checks, substantial review |
| Smart worker | `xhigh` | Difficult implementation or ambiguity across boundaries |
| Deep worker | `max` | Exceptional, very difficult, high-impact reasoning |

Use the lowest role that can satisfy the acceptance criteria. State the concrete hard-reasoning reason before using `xhigh` or `max`. Keep reasoning effort separate from elapsed-work budgets such as `small`, `normal`, and `deep`.

Prefer `fork_turns: "none"` for focused scouts and workers. Include every essential safety, authority, and task constraint in a fresh-context brief. Use a bounded positive history count only when prior turns materially affect the assignment. A full-history fork inherits the parent model and effort and cannot be combined with model or effort overrides.

Treat `ultra` as a high-stakes parent coordination mode, not a routine child role.

## Assign And Launch

Read [references/briefs-and-ledger.md](references/briefs-and-ledger.md) before the first spawn in a non-trivial milestone.

- Mark every stream `read-only` or `write-enabled`.
- Give write-enabled agents exact, disjoint ownership and say they are not alone in the workspace.
- For a hard read-only boundary, use an enforced role/sandbox covering every consequential side effect or a disposable isolated snapshot with external mutation paths removed. Otherwise keep that scope in the parent. A prompt is not enforcement.
- For an advisory read-only stream, use bounded before/after detection. Read [references/read-only-boundaries.md](references/read-only-boundaries.md).
- Give leaf agents a direct boundary not to spawn. Allow nesting only for distinct evidence after the parent records a progress delta, reserves runs from the same cap, and grants the exact nested scope.
- Let agents message relevant peers directly when they discover a dependency; require the receiving agent and parent to get the concise evidence handoff.
- Use tool fields for model, effort, role, and history. Do not put tool-field pseudo-markers in the child prompt.
- Ask critics for symptoms, measurements, reproduction, and uncertainty—not a dictated repair.
- If evidence falsifies the brief's mechanism, require the worker to report the contradiction and replacement hypothesis. The worker stays inside its authority. The parent resolves scope or architecture changes within existing user authorization; seek user input only when the change requires new authority or an essential decision.

Maintain a compact ledger with the stable milestone ID, scope keys, ownership, child-run cap, spawn/follow-up/nested counts, reservations, remaining budget, launch batches, progress deltas, lifecycle state, received evidence, and terminal synthesis point. Announce skill use once per logical chain; later updates should report only material scope, budget, or state changes.

## Coordinate Without Blocking

Continue useful parent work while children run. Use:

- `send_message` for an in-brief correction, dependency handoff, or already-requested evidence/checkpoint. It consumes no run; material scope expansion may not hide in a message.
- `followup_task` for a distinct continuation or scope expansion on an existing child. It always consumes one child run.
- `wait_agent` as the native mailbox wait when the next parent action needs a child update. It wakes for child mail, user steering, or timeout; timeout is only the end of that wait window.
- `list_agents` for reconciliation or a concrete lifecycle decision, never as a timer-driven status check or substitute for the child's final evidence.

Do not describe `wait_agent` as polling. Use the longest bounded mailbox wait compatible with the host's user-update rules and the current decision point; do not loop a short timer merely to generate activity. On timeout, say only that no update arrived, continue useful work, or enter another mailbox wait when the result remains blocking. Do not call `list_agents` solely because a wait timed out.

Before interruption for lateness, request a checkpoint, wait a reasonable window, and compare against the recorded hard decision point. Inspect the interrupt result; `previous_status.completed` means the child completed by interrupt time.

If it is not already active, load `wait-for-subagents-patiently` for detailed budgets, stall evidence, long-running work, or intervention decisions. Never recursively reload it. Explicit domain patience rules, including "do not force an answer," override generic elapsed-time guidance.

## Reconcile And Gate More Work

After resume, steering, compaction, or a new user message:

1. Call `list_agents`.
2. Recover queued or final messages and inspect expected artifacts when status is incomplete.
3. Reuse, steer, wait for, follow up, or explicitly supersede the existing child.
4. Start a replacement only when the original is obsolete, irrecoverable, outside scope, or past its hard decision point after checkpointing; it remains subject to the child-run and progress-delta gates.

Runs launched from the same parent state form a batch. The initial batch needs budget but no prior delta. Before any later batch—including a follow-up, retry, replacement, or nested run—require both unreserved budget and a new parent-owned delta recorded after the preceding batch: an integrated artifact, newly passed proof, closed decision, verified evidence, or advanced goal metric. A consumed child answer counts only after parent verification or integration. A delta unlocks one declared batch and never replenishes the cap. Without both, consolidate or execute in the parent.

Use one read-only reviewer when independent review is required or would resolve a named uncertainty at a stable evidence-bearing checkpoint. Do not review moving scope. Two consecutive review cycles without new implementation or evidence stop further review until the state materially changes.

After a failed or regressive repair wave, stop equivalent fanout and run a diagnosis checkpoint before assigning another fix.

## Verify And Hand Off

- Consume each required child's actual final answer; `completed` status alone is not a result.
- Verify important claims against current files, commands, tests, logs, or UI state.
- Reuse scoped child evidence after checking its relevance and artifact identity. Repeat exploration or checks only to resolve a specific gap, conflict, integration risk, or changed state.
- Run checks appropriate to the affected behavior and all required project checks. Once those pass, broaden or repeat testing only when new changes, failures, or unresolved concerns justify it.
- Compare post-work state with the baseline. For read-only scopes, investigate any change before using the result.
- Classify write changes by declared ownership and preserve unrelated user work.
- Report the outcome, changed files, validation, child lifecycle facts that matter, omitted results, remaining risks, and open blockers.

Return `done`, `partial`, or `blocked`; never convert activity into completion evidence.
