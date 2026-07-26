# Briefs and coordination ledger

## Child brief

Use a compact, self-contained brief:

```text
Stream: <short label>. <read-only/write-enabled>.

Objective: <one concrete outcome>
Scope: <exact paths, modules, artifacts, or questions>
Scope key: <milestone:objective:paths:mode>
Coupling: <independent scope or one coupled outcome owned end to end>
Allowed changes: <none or exact ownership>
Worker condition: <role and effort; fresh or bounded inherited context>
Expected budget: <small/normal/deep; checkpoint; hard decision point>
Authority and safety: <task-local permissions and prohibitions>
Contradiction rule: if evidence falsifies the requested mechanism, report evidence and a replacement hypothesis without exceeding authority
Dependencies: <none or named peer and required handoff>
Subagent boundary: Complete this directly. Do not spawn unless this brief explicitly grants it.
Nested run authority: <none, or exact reserved scope granted by the parent>
Acceptance:
- <observable criterion>
- <observable criterion>
- <observable criterion>

Return:
Outcome: done/partial/blocked
Changes: exact files or none
Validation: commands/checks and results
Findings: prioritized bullets
Evidence: paths, line refs, artifacts, or rollout ids
Peer handoffs: messages sent/received or none
Open questions: blockers only
```

For a write-enabled child, add:

```text
You are not alone in the workspace. Do not revert unrelated edits; adapt to changes made by others.
```

Do not ask every child for a plan when the assignment is already bounded. Do not send the intended answer, hidden diagnosis, or another child's conclusions unless the dependency requires them.

## Child-run accounting

Before the initial batch, and after resume or compaction, record:

```text
stable milestone ID = M
independent scopes = N
initial cumulative child-run cap = C
cumulative child runs used = U
reserved nested runs = R
remaining unreserved child-run budget = B = C - U - R
configured/observed free child slots = S
fanout now = min(N, B, S)
queued scopes = N - fanout now
```

Debit every `spawn_agent` and `followup_task` at any depth, including retries, replacements, failed calls, and interrupted runs. Reserve nested allowance before granting it; each nested spawn converts one reservation into one used run. Release unused reservations only after reconciliation.

`send_message` is free only for an in-brief correction, handoff, or already-requested evidence/checkpoint. A new objective, ownership boundary, deliverable, or acceptance criterion requires a budgeted child run.

## Ledger

Keep the ledger small enough to survive compaction:

| Field | Record |
| --- | --- |
| Milestone and terminal synthesis point | Stable ID, name, and stopping condition |
| Acceptance | 3-6 observable criteria |
| Child-run budget | Initial cap, used by tool/depth, nested reserved, remaining |
| Launch batches | Runs and parent delta unlocking each later batch |
| Capacity | Configured limit, active children, free slots |
| Scope keys | Child, mode, ownership, status |
| Evidence received | Final answer/artifact identity and parent verification |
| Rejected paths | Candidate and reason |
| Progress delta | Verified change, proof, evidence, decision, or metric; unused or batch unlocked |
| Next action | Parent action, wait, queued scope, or handoff |

Update it after any spawn/follow-up at any depth, reservation change, meaningful message, final answer, interruption, progress delta, or scope change. Do not narrate unchanged polls.

## Peer handoffs

Use direct peer messaging when a child discovers a dependency another active child needs. Send only:

```text
Dependency: <what changed or was discovered>
Evidence: <path, line, artifact, or check>
Impact on your scope: <specific consequence>
Requested action: <one bounded response>
```

Require the sender to note the handoff in its final answer. The parent remains responsible for resolving disagreement and verifying the integrated result.

## Baselines

For every exact read-only scope, compare a bounded recursive manifest regardless of Git tracking or ignore status: lexical relative path, existence, entry type, regular-file SHA-256, and non-dereferenced link/reparse kind plus target identity. Inventory a link-valued scope root itself and never recurse through links. In Git also compare the bounded index identity; use status and diffs as diagnostics only where they cannot cross a link/reparse boundary, and record an explicit skip reason otherwise. Do not hash or enumerate unrelated personal trees.

After a read-only stream, compare the same bounded surface. Treat unexpected files or edits as a failed read-only invariant until explained and recovered safely.
