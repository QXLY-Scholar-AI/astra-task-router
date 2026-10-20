<!-- ASTRA-TASK-ROUTER:START -->
## Task routing

Use the installed astra-task-router skill for bounded model routing when the host supports subagents and the user authorizes delegation. Preserve the user's selected main model. Do small tasks directly; do not spawn merely to use the router.

Routine extraction/formatting: prefer gpt-6-luna. Implementation and normal analysis: prefer gpt-6.1-sol, then gpt-6-sol. Difficult research judgments and independent acceptance reviews: prefer gpt-6-astra. Check the host's current model list and supported reasoning efforts before selecting; do not invent availability or substitute an external API.

Default to one worker. Multiple workers need independent scopes and an actual concurrency benefit. Never allow overlapping file writes. Send only necessary source material, a bounded objective and checkable acceptance criteria. Check evidence and artifacts before accepting the result. One focused correction is the default; if that fails, replan or solve in the main thread. Do not repeat the full task in both places.

If the host cannot select models, execute in the main thread and state that routing was not performed. Configuring instructions does not change the currently running model. Never edit provider, credential, sandbox or global model settings merely to activate this policy.
<!-- ASTRA-TASK-ROUTER:END -->
