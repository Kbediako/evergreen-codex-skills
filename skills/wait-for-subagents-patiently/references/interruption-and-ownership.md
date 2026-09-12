# Interruption and ownership

Read before interrupting a child or taking over its write scope.


Interrupt only for a concrete reason:

- the user asks to stop;
- the scope became obsolete;
- the child violates scope or permissions;
- scarce resources or external side effects require intervention;
- a blocking hard decision point passed, with prior checkpointing only when the real boundary allowed it.

Act promptly on an explicit user stop or an urgent safety, authorization, resource, or consequential-side-effect boundary; do not delay the necessary interruption to request or await a checkpoint. Reconcile afterward. Ordinary lateness or a generic elapsed-time estimate does not create this exception.

Inspect the interrupt result immediately. If the returned previous status indicates completion, classify the child as completed by interrupt time, even if the final answer is delivered separately. Recover and consume the actual final answer before using the result; until then, report completion with the final answer not yet consumed. Do not call it stalled or restart it merely because the answer was not embedded in the response.

Interruption does not imply rollback or cancellation of already-launched operations. Before the parent or a replacement takes overlapping write ownership, reconcile affected paths and retained changes, and establish that the previous writer and its known outstanding operations have stopped writing that scope or are isolated from it. Establish one current owner; unresolved writers or consequential effects block overlapping takeover. Observe or stop underlying operations only through their exact identities and existing authorization, preserving unrelated work.
