<!-- kit_ap:start -->
<!-- Managed by KIT Adaptive Preregistration (https://github.com/polarizetech/kit-adaptive-preregistration.git). Don't edit between these markers: change the kit, then run `.agents/bin/kit_ap update`. -->

# Agent protocols

This repo uses **KIT Adaptive Preregistration**: agent protocols that are maintained in one central repo and vendored into `.agents/`. Every agent follows them, whatever the tool (Claude Code, Codex, Copilot, Cursor, Gemini, ChatGPT…).

- The rules in this block and the documents in `.agents/protocols/` are binding. If a task conflicts with one, stop and say so before doing the task.
- Project-specific instructions (outside these markers, or in nested `AGENTS.md` files) may add to the protocols. If one contradicts a protocol, ask the user which wins.
- Don't edit files in `.agents/` or text between the `kit_ap` markers. Updates overwrite them. To change a protocol, propose the change to the user as an edit to the kit repo.
- If a session-start message says the protocols are out of date, tell the user once. Don't update without their go-ahead. If your tool has no hooks, run `.agents/bin/kit_ap check` once at the start of a session.

## Conversation logging

This repo logs LLM conversations to the branch's PR and to `conversations/` via `.agents/tools/convo-log` (see `.agents/protocols/CONVERSATIONS.md`).
- Work on a branch, not `main`. Before the first reply on a new branch, open a draft PR so the log has somewhere to post:
  `git commit --allow-empty -m "start: <topic>" && git push -u origin HEAD && gh pr create --draft --fill`
- Include the branch's conversation log file in your commits.
- Never edit, rewrite, or delete conversation logs or their PR comments.
- If your tool has no hooks (see CONVERSATIONS.md §4), at the end of each turn run:
  ```bash
  .agents/tools/convo-log add --role user --tool <tool> --no-sync <<'MSG'
  <the user's message, verbatim>
  MSG
  .agents/tools/convo-log add --role assistant --tool <tool> <<'MSG'
  <your final reply, verbatim>
  MSG
  ```

<!-- kit_ap:end -->
