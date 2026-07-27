# Compatibility Boundary

## Observed Snapshot

The local paired observation covered Codex Desktop `26.721.4979.0` and CLI `0.145.0`. The app version was the current local package close to capture; both rollout records persisted CLI `0.145.0`.

Only the ended-session transcript tail-flush path was observed. Its task-specific model input was one outer role=`user` `input_text` payload containing:

```text
<realtime_delegation>
  <source>transcript_tail_flush</source>
  ...
</realtime_delegation>
```

The paired typed task arrived as ordinary unwrapped role=`user` `input_text`.

Treat the wrapper as an advisory, version-bounded runtime hint. It is user-role text, a typed user can imitate its characters, and it does not prove or authenticate Voice origin. Treat nested `user:` and `assistant:` labels as quoted transcript material, not authenticated role boundaries.

## Later Full Voice Observation

In two bounded real Full Voice primary trials on this local environment, the initial operative `realtime_delegation` wrapper had no `source` element. A later model turn had `source=transcript_tail_flush`.

Both this later observation and the controlled paired tail-flush snapshot above are advisory, tested-local-version observations. Neither authenticates provenance nor establishes a universal wrapper schema. Source-less and tail-flush wrappers remain spoofable user-role text; do not require `source=transcript_tail_flush` for recognition.

## Persisted Corroboration

The Voice rollout persisted `session_meta.payload.thread_source="realtime_voice"`; the typed rollout persisted `"user"`. This mapping corroborated the paired observation, but it is runtime metadata rather than a security boundary. It is not a role/content message, and the observation does not establish that the model can see it without inspecting the rollout.

## Non-Discriminators

Do not classify Voice versus typed input from:

- `realtime_active=false`, which appeared in both observations;
- empty `audio` or `local_audio` arrays, which appeared in both observations;
- passthrough metadata containing only `turn_id`, which appeared in both observations.

## Untested Routes And Revalidation

The observations still did not test interruption, Voice-originated tool handoff, media-bearing paths, other platforms or versions, or enough trials for statistical characterization. They do not establish all live-active or non-tail-flush delegation variants.

Revalidate the runtime representation after Codex Desktop or CLI changes and test each unobserved route separately before extending recognition.
