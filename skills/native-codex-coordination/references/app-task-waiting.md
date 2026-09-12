# App task and thread waiting

For a Codex app task or thread:

1. When the active runtime exposes `wait_threads`, call it directly with the exact task/thread ID. If the app event-wait tool is unavailable, report that missing capability; do not invent a callable tool or substitute an external monitor. Preserve every returned cursor unchanged and supply it to the next wait. Continue in the active turn by default.
2. Never route the task to `long-poll-wait`, a custom external awaiter, or another external-monitoring path.
3. Use a scheduled continuation only after verifying that scheduling is authorized, the next context can call `wait_threads` and is authorized for the task/thread, and that context can durably retain the cursor or reacquire and rebind it from preserved state.
4. After expiry, restart, or intervention, revalidate the task/thread ID and latest state, then reacquire and rebind the cursor before waiting again.
5. If the scheduled-context or rebinding proof is unavailable, return `needs-scheduled-handoff` with the task/thread ID, preserved cursor, latest state and timestamp, plus the exact host, tool, context, authorization, and cursor-reacquisition requirements.
