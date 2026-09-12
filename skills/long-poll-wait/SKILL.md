---
name: long-poll-wait
description: Monitor an external process, CI run, or cloud job until an authoritative terminal result or explicit handoff. Excludes native Codex children and app tasks.
---

# Long poll wait

Observe one external operation through its stable identity and authoritative status source. Use [patient waiting](../wait-for-subagents-patiently/SKILL.md) for native children and the app's event-wait tool for Codex tasks or threads.

## Bind the observation

Record the operation ID, source and handle, latest state and timestamp, success/failure conditions, relevant artifacts, and any real stop deadline. Bind handles to the originating tool, host, and operation; IDs from different layers are not interchangeable.

Reuse a verified existing observation. When choosing or recovering a path, use the first currently callable, configured, authorized option:

1. A source-native event, watch, stream, or subscription.
2. The exact existing process or terminal session's wait/resume tool.
3. The authoritative pull endpoint.

Documentation alone does not make a path available. Do not restart the underlying job or create a duplicate monitor to recover observation.

## Continue until the outcome is known

Continue in the active turn by default. Keep operation duration, tool blocking limits, user-update cadence, and provider pull timing separate. Use the longest supported wait that preserves host responsiveness and respects the next real decision or resource boundary. Yield and resume the same observation when needed.

Record material progress on wake and give decision-relevant updates. A local wake or user update does not authorize an extra provider pull. For pull-only sources, honor `Retry-After` and provider guidance; otherwise back off unchanged state and add jitter when monitors could synchronize. Preserve the next eligible observation time and reset backoff only after material progress.

On expiry, context change, observation loss, or parent intervention, revalidate the operation and handle. Reacquire or select another authorized path for the same operation. If none is usable, report an observation blocker with the last verified state; this does not establish job failure.

Read [continuation and handoff](references/continuation-and-handoff.md) when monitoring must transfer to another context, scheduling is needed, or an optional observer role is being configured. Do not assume live streams or process handles survive that transfer. Schedule only after verifying receiving-context capability, authorization, and sufficient durable state.

## Respect the observer boundary

The observer does not restart, cancel, remediate, or modify the operation. Return `intervention-required` with the evidence and proposed action to the parent, which retains decision and execution authority.

Quiet periods are normal. A stall claim needs sustained lack of progress supported by independent signals, such as status and log movement. Repeated reads of one status are not independent evidence.

Stop observing at a terminal result, explicit stop, requested observation deadline, irreparable observation failure, or declared nonterminal handoff. Ending observation does not cancel the job. Report `observation-stopped` for a stop or deadline before termination, or `needs-scheduled-handoff` when required continuity cannot be established.

## Report and retire the monitor

Report the outcome, operation ID, authoritative evidence, final timestamp, and material uncertainty. For nonterminal handoffs, preserve the handle, host/tool requirements, expiry and reacquisition method, provider timing, next observation time, and stop conditions using the handoff reference.

Job completion and monitor retirement are separate. Preserve remaining monitoring-continuation identities so the parent can retire exact owned continuations within existing authority. Report any unverified retirement as a residual blocker. Do not claim success from elapsed time, log silence, monitor exit, or a nonterminal status.
