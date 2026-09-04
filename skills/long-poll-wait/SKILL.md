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
- latest observed timestamp and state.

## Choose The Observation

Use the first path that is currently callable, configured, and authorized:

1. Source-native watch, stream, subscription, or event cursor.
2. The exact existing process or terminal session's wait/resume tool.
3. The authoritative pull endpoint.

Provider documentation alone does not make a path available. Do not replace an available wait with sleeps, repeated status snapshots, or a second monitor.

## Choose The Continuation

- Continue in the active turn when the operation is expected to finish within it.
- Evaluate the observation path from the context that will perform the next observation. Use a scheduled continuation only when scheduling is authorized there and the path is callable, authorized, and durable or demonstrably reacquirable from preserved state.
- A live stream, yielded command, or PTY/session handle defaults to active-turn continuation. Schedule it only after a capability check proves that the scheduled context can resume or reconnect to that exact observation; otherwise return `needs-scheduled-handoff`.
- A scheduled pull-only monitor performs one provider-compliant pull per wake; scheduling does not turn pull polling into an event wait.
- If the scheduled context cannot use the former path, rerun the observation hierarchy there. When no compatible scheduled path is verified, return `needs-scheduled-handoff` with the preserved monitor state. This is nonterminal and is not an observation failure.

The optional Astra Medium role in [references/awaiter-role.toml](references/awaiter-role.toml) is an active-turn external observer template, not an auto-registered agent. Install it as `awaiter.toml` under the user or project `.codex/agents/` directory, start a fresh task so the role catalog reloads, and verify the resolved role before first use. Its read-only sandbox is defense in depth, not proof against live parent overrides or mutating connectors. When hard isolation is required and cannot be verified, keep the monitor in the parent or use an isolated observer.

## Observe To Terminal State

1. Start from the authoritative source and stable identifier.
2. Await the next event or process completion, or make the next permitted pull, without restarting the underlying job.
3. Record timestamp, state, and material progress on wake.
4. Emit a concise checkpoint on state change or a user-relevant decision point; do not narrate unchanged observations.
5. While status remains nonterminal, resume the verified path. Reacquire or reselect it after a context change, expiry, restart, replacement, or parent intervention; never assume the former handle or identifier survived.
6. Stop at terminal state, explicit user stop, an irreparable observation failure, or a declared nonterminal handoff.

For a pull-only source, honor `Retry-After` or provider guidance. Otherwise use bounded exponential backoff with jitter for fanout, cap it to the task's decision needs, and reset only after material progress. Never impose a universal 30-60 second cadence.

## Judge A Possible Stall

- Treat temporary no-progress windows as normal.
- Require sustained lack of progress plus at least two signals, such as status and log/event movement.
- Distinguish an observation failure from an underlying job failure.
- The observer does not restart, cancel, remediate, or otherwise mutate the underlying operation.
- Return `intervention-required` with the reason, proposed action, current state, and evidence. The parent retains approval and execution authority.
- After an authorized parent intervention, revalidate the operation identity and observation path, rebinding them when necessary.

## Handoff

Report:

- one outcome: terminal state, verified observation blocker, `needs-scheduled-handoff`, or `intervention-required`;
- stable external identifier;
- observation type and endpoint/session/cursor;
- durability or expiry, reacquisition method, required host/tool/connector and authorization, and continuation-compatibility result;
- final timestamp and key progress fields;
- log, manifest, and artifact evidence;
- provider cadence or current backoff state;
- parent interventions observed or `none`;
- residual risks for non-success terminal states.

For `needs-scheduled-handoff`, also preserve the next run or cadence, terminal/failure conditions, stop or user-input condition, and schedule/task identity if one was created. Do not claim scheduled continuity without evidence that its execution context can reacquire the observation.

Do not claim success from elapsed time, log silence, monitor exit, or a nonterminal status.
