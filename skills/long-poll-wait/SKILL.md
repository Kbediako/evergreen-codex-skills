---
name: long-poll-wait
description: Await or monitor external long-running jobs, operating-system processes, CI pipelines, cloud runs, remote training, or release checks until terminal status. Select an authorized observation path separately from active-turn or scheduled continuation; poll only pull-only sources. Never use for native Codex child or app-task lifecycle.
---

# Long Poll Wait

## Keep The Boundary

Use this skill only for external jobs, processes, services, CI, cloud runs, training, or release checks with a stable status source.

Route native Codex child silence, wait timeouts, reconciliation, checkpointing, and interruption to [wait-for-subagents-patiently](../wait-for-subagents-patiently/SKILL.md).

Use the current app-task event wait directly for Codex tasks or threads; never route them to an external awaiter.

## Record The Monitor

Capture:

- stable run, job, process, or check identifier;
- observation type and the currently callable endpoint, cursor, revision, or session ID;
- observation durability or expiry, reacquisition method, and required host, tool or connector, and authorization;
- continuation mode: active turn or scheduled, plus schedule/task identity when created;
- compatibility result for the context that will perform the next observation;
- terminal success and failure states;
- logs, events, and artifact paths;
- provider limits, `Retry-After`, backoff policy, and intervention authority;
- next eligible observation time and any requested observation deadline or stop condition;
- latest observed timestamp and state.

## Choose The Observation

Reuse a verified existing observation for the same operation. When selecting or reselecting a path, use the first option that is currently callable, configured, and authorized:

1. Source-native watch, stream, subscription, or event cursor.
2. The exact existing process or terminal session's wait/resume tool.
3. The authoritative pull endpoint.

Provider documentation alone does not make a path available. Do not replace an available wait with sleeps, repeated status snapshots, or a second monitor.

Bind each continuation handle to its originating tool, host, and operation. Resume it through that tool's supported interface; identifiers from different observation layers are not interchangeable.

## Choose The Continuation

- Continue in the active turn while that continuation remains viable; duration estimates alone are not stop deadlines.
- When scheduled continuation is needed, verify scheduler availability and authorization and evaluate observation capabilities in the receiving context. Prefer resuming the existing observation; otherwise reapply the observation hierarchy for the same stable external operation. Schedule only after verifying a compatible path and sufficient preserved state.
- A live stream, yielded command, or PTY/session handle defaults to active-turn continuation. Do not assume the handle transfers to another context; verify resumption or select another authorized observation path for the same operation without restarting it.
- A scheduled pull-only monitor performs at most one provider-compliant pull per wake. Preserve the next eligible observation time across wakes and context changes; an early wake makes no pull and retains or adjusts the existing authorized schedule. Scheduling does not turn pull polling into an event wait.
- When required scheduled continuation cannot be established, return `needs-scheduled-handoff` with the preserved state and exact missing scheduler, path, authorization, or continuity requirement. This is nonterminal and is not an underlying job failure.

The optional Astra Medium role in [references/awaiter-role.toml](references/awaiter-role.toml) is an active-turn external observer template, not an auto-registered agent. Install it as `awaiter.toml` under the user or project `.codex/agents/` directory, start a fresh task so the role catalog reloads, and verify the resolved role before first use. Its read-only sandbox is defense in depth, not proof against live parent overrides or mutating connectors. When hard isolation is required and cannot be verified, keep the monitor in the parent or use an isolated observer.

## Observe To Terminal State

Keep operation duration, blocking-call limits, user-update cadence, and provider pull timing separate. Use the longest supported wait compatible with the active tool schema, host responsiveness requirements, and the next real decision or resource boundary. Yield and resume the existing observation when needed; a local wake or user update does not authorize an extra provider pull or establish job failure.

1. Start from the authoritative source and stable identifier.
2. Await the next event or process completion, or make the next permitted pull, without restarting the underlying job.
3. Record timestamp, state, and material progress on wake.
4. Emit a concise checkpoint on state change or a user-relevant decision point. Avoid redundant updates while honoring the host's communication requirements.
5. While status remains nonterminal, resume the verified path. Reacquire or reselect it after a context change, expiry, restart, replacement, or parent intervention; never assume the former handle or identifier survived.
6. Stop at terminal state, explicit user stop, a requested observation deadline, an irreparable observation failure, or a declared nonterminal handoff. For a user stop or observation deadline before job termination, report `observation-stopped` with the reason and the operation's last known state; ending observation does not cancel the job.

For a pull-only source, honor `Retry-After` or provider guidance before any task-driven timing cap. Otherwise use bounded exponential backoff with jitter for fanout, cap it to the task's decision needs, and reset only after material progress. Never impose a universal 30-60 second cadence.

## Judge A Possible Stall

- Treat temporary no-progress windows as normal.
- Require sustained lack of progress plus at least two signals, such as status and log/event movement.
- Distinguish an observation failure from an underlying job failure.
- The observer does not restart, cancel, remediate, or otherwise mutate the underlying operation.
- Return `intervention-required` with the reason, proposed action, current state, and evidence. The parent retains approval and execution authority.
- After an authorized parent intervention, revalidate the operation identity and observation path, rebinding them when necessary.

## Handoff

Report:

- one outcome: terminal state, verified observation blocker, `observation-stopped`, `needs-scheduled-handoff`, or `intervention-required`;
- stable external identifier;
- observation type and endpoint/session/cursor;
- durability or expiry, reacquisition method, required host/tool/connector and authorization, and continuation-compatibility result;
- final timestamp and key progress fields;
- log, manifest, and artifact evidence;
- provider cadence, current backoff state, next eligible observation time, and any observation deadline or stop reason;
- parent interventions observed or `none`;
- residual risks for non-success terminal states.

For `needs-scheduled-handoff`, also preserve the next run or cadence, terminal/failure conditions, stop or user-input condition, and schedule/task identity if one was created. Do not claim scheduled continuity without evidence that its execution context can reacquire the observation.

For a terminal job outcome or `observation-stopped`, preserve the terminal evidence or stop reason, last verified job state and timestamp, and any remaining monitoring-continuation identities. The parent retires the exact owned monitoring continuation through available tools within existing authorization. The observer reports that need without acquiring scheduling powers. If retirement cannot be verified, report the residual continuation and blocker; do not claim monitoring has fully stopped. Job completion and monitor retirement are separate outcomes. This does not authorize changing the underlying job.

Do not claim success from elapsed time, log silence, monitor exit, or a nonterminal status.
