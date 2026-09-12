# Continuation and handoff

Read when scheduling, transferring observation to another context, or configuring an optional observer.


- Continue in the active turn while that continuation remains viable; duration estimates alone are not stop deadlines.
- When scheduled continuation is needed, verify scheduler availability and authorization and evaluate observation capabilities in the receiving context. Prefer resuming the existing observation; otherwise reapply the observation hierarchy for the same stable external operation. Schedule only after verifying a compatible path and sufficient preserved state.
- A live stream, yielded command, or PTY/session handle defaults to active-turn continuation. Do not assume the handle transfers to another context; verify resumption or select another authorized observation path for the same operation without restarting it.
- A scheduled pull-only monitor performs at most one provider-compliant pull per wake. Preserve the next eligible observation time across wakes and context changes; an early wake makes no pull and retains or adjusts the existing authorized schedule. Scheduling does not turn pull polling into an event wait.
- When required scheduled continuation cannot be established, return `needs-scheduled-handoff` with the preserved state and exact missing scheduler, path, authorization, or continuity requirement. This is nonterminal and is not an underlying job failure.

The optional Astra Medium role in [awaiter-role.toml](awaiter-role.toml) is an active-turn external observer template, not an auto-registered agent. Only when role configuration is requested, install it as `awaiter.toml` under the user or project `.codex/agents/` directory, start a fresh task so the role catalog reloads, and verify the resolved role before first use. Before launching a native observer, load [native-subagents-first](../../native-subagents-first/SKILL.md) unless already active and apply its run accounting, ownership, and effective-permission checks. Ordinary parent observation does not require that dependency. Its read-only sandbox is defense in depth, not proof against live parent overrides or mutating connectors. When hard isolation is required and cannot be verified, keep the monitor in the parent or use an isolated observer.


## Preserve a resumable handoff


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
