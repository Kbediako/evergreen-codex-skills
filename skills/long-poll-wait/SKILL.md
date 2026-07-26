---
name: long-poll-wait
description: Monitor external long-running jobs, operating-system processes, CI pipelines, cloud runs, remote training, or release checks until terminal status. Use only for externally observable operations, not for native Codex child-agent lifecycle.
---

# Long Poll Wait

## Keep The Boundary

Use this skill only for external jobs, processes, services, CI, cloud runs, training, or release checks with a stable status source.

Route native Codex child silence, wait timeouts, reconciliation, checkpointing, and interruption to [wait-for-subagents-patiently](../wait-for-subagents-patiently/SKILL.md).

## Record The Monitor

Capture:

- stable run, job, process, or check identifier;
- status command or endpoint;
- terminal success and failure states;
- logs, events, and artifact paths;
- polling cadence and intervention authority;
- latest observed timestamp and state.

## Poll To Terminal State

1. Query the authoritative status source.
2. Record timestamp, state, and material progress.
3. Emit a concise checkpoint on state change or at the agreed cadence.
4. Keep polling while the state is nonterminal and observation remains possible.
5. Relaunch a failed monitor from the stable identifier without restarting the underlying job.
6. Stop only at terminal state, explicit user stop, or an observation failure that cannot be repaired.

Use moderate cadence:

- 30-60 seconds during active progress;
- up to 60 seconds during slow or noisy phases;
- immediate polling after a meaningful state transition.

Respect service limits and any task-specific cadence. If the external source
requires a longer interval, use a nonblocking monitor or wakeup and remain
available for user updates.

## Judge A Possible Stall

- Treat temporary no-progress windows as normal.
- Require sustained lack of progress plus at least two signals, such as status and log/event movement.
- Distinguish an observation failure from an underlying job failure.
- Intervene only within the user's authority and the external system's policy.
- Record intervention reason, timestamp, command or API action, and resulting state.
- Continue monitoring after intervention until terminal state or a verified observation blocker.

## Handoff

Report:

- final terminal state, or the exact verified observation blocker;
- stable external identifier;
- final timestamp and key progress fields;
- log, manifest, and artifact evidence;
- interventions performed or `none`;
- residual risks for non-success terminal states.

Do not claim success from elapsed time, log silence, monitor exit, or a nonterminal status.
