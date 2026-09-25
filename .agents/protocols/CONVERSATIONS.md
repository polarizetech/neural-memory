# Conversation logging

**License:** CC BY 4.0, from [KIT Adaptive Preregistration](https://github.com/polarizetech/adaptive-preregistration). Reuse it with credit.

Every LLM conversation on a branch is recorded twice:

1. **On the branch's PR:** one comment per turn. It's searchable on GitHub and is the history you read later.
2. **In git:** a JSONL log file committed alongside the work. It's searchable with `git grep`, and other tools can reuse it.

`.agents/tools/convo-log` does both. Hooks call it automatically where the tool supports them. For tools that don't, it's run by hand or by the agent.

---

## 1. What gets recorded

| Rule | Detail |
|---|---|
| One comment per turn | Consecutive user messages are merged into **one** comment. Each assistant reply is **one** comment. |
| Text only | Your prompts and the assistant's final reply for the turn. Tool calls, diffs, and thinking are **not** logged (the commits already hold the diffs). |
| Secrets redacted | Common credential shapes (provider API keys, bearer tokens, JWTs, private keys, passwords in URLs, and `NAME=value` settings whose name mentions a key, secret, token or password) become `[redacted]` before anything is written or posted. This is best-effort pattern matching, not a guarantee: don't paste secrets into a logged session. |
| Order | A user comment is only posted once the reply arrives (so bursts of messages group). Anything still waiting is posted when the session ends, or by running `.agents/tools/convo-log sync --flush`. |
| No PR yet | Messages queue in the log and post, in order, on the first reply after the branch has a PR (or run `.agents/tools/convo-log sync`). |
| Never blocks | If logging fails, it prints a warning and exits 0. The agent carries on. |

## 2. Where the log lives

The default is `conversations/<branch>.jsonl`, where `/` in branch names becomes `-`.

To change it, add an optional `.convo-log.json` at the repo root:
```json
{
  "dir": "conversations",
  "paths": {
    "^creation/(.+)$": "creations/{1}/conversation.jsonl",
    "^exp/(.+)$":      "experiments/{1}/chat.jsonl"
  }
}
```
Each key in `paths` is a regex matched against the branch name, and the first match wins. `{1}`, `{2}`… are the regex capture groups, and `{branch}` is the full branch name. Branches that match nothing go to `dir`.

Other KIT Adaptive Preregistration modules can add routes in `.agents/config/convo-log.d/*.json` (same format). For example, `experiment-pr-log` routes `experiment/<EID>` to `experiments/<EID>/conversation.jsonl`. Routes in the repo's own `.convo-log.json` match first.

Each line in the log:
```json
{"id":"86675602508e","ts":"2026-09-24T10:14:03-07:00","role":"user","tool":"claude","model":null,
 "session":"s1","text":"make it blue","comment":"https://github.com/<you>/<repo>/pull/7#issuecomment-…"}
```
`comment` is `null` until posted. It then holds the link to the PR comment, so other files can link to a specific exchange by `id`.

Each PR comment starts with a hidden marker, used for de-duplication and for scripts:
```
<!-- convo v1 role=user tool=claude session=s1 ids=86675602508e,1cae9d51faaa -->
**Your Name** · via Claude Code · 2026-09-24 10:14
```
The name comes from `git config user.name`.

## 3. Install

This protocol is the `convo-log` module of KIT Adaptive Preregistration, installed by default:
```bash
kit_ap init /path/to/repo            # or, in a repo that already has KIT Adaptive Preregistration:
.agents/bin/kit_ap add convo-log
```
That installs `.agents/tools/convo-log`, this document, `.github/hooks/kit_ap-convo-log.json` and the Claude Code hooks (merged into `.claude/settings.json`), and adds the agent instructions to the managed block in `AGENTS.md`.

Requirements: Python 3, git, and the GitHub CLI logged in (`brew install gh && gh auth login`).

Then commit the new files. Every new branch needs a draft PR before its comments can post. The agent instructions ask the agent to open one, or you can run:
```bash
git commit --allow-empty -m "start: <topic>" && git push -u origin HEAD && gh pr create --draft --fill
```

## 4. Per-tool setup

| Tool | How it's captured | Reliability |
|---|---|---|
| **Claude Code** | Hooks in `.claude/settings.json`: `UserPromptSubmit` → your prompt, `Stop` → `last_assistant_message`, `SessionEnd` → posts anything still waiting. | High |
| **Codex CLI** | `notify` in `~/.codex/config.toml`. Each turn it passes your messages (`input-messages`) and the final reply (`last-assistant-message`). | High |
| **Copilot / agents in VS Code** | Hooks (Preview) in `.github/hooks/kit_ap-convo-log.json`: `UserPromptSubmit` → prompt, `Stop` → the reply, read from the transcript. The transcript format isn't a stable API, so the reply can be missed. | Medium |
| **ChatGPT, Claude.ai, Gemini, any chat UI** | No hooks. Log by hand (below). | Manual |
| **Any other agent** | The instructions in `AGENTS.md` tell it to run `convo-log add` each turn. | Low. Agents forget. |

**Claude Code:** nothing to do after install. Set `CONVO_MODEL=<model name>` in your shell if you want the model shown on comments.

**Codex CLI:** `notify` is a global setting. The script only acts inside a git repo and logs to whichever repo Codex ran in. Point it at any installed copy:
```toml
notify = ["python3", "/absolute/path/to/some-repo/.agents/tools/convo-log", "capture", "codex"]
```

**VS Code / Copilot:** leave the `chat.useClaudeHooks` setting **off**. Otherwise VS Code also runs the Claude Code hooks and labels its messages as Claude Code.

**Manual (ChatGPT etc.):** from inside the repo:
```bash
pbpaste | .agents/tools/convo-log add --role user --tool chatgpt --no-sync
pbpaste | .agents/tools/convo-log add --role assistant --tool chatgpt --model gpt-5
.agents/tools/convo-log sync --flush        # when you're done
```
For a long chat, paste the whole exported thread as a single assistant entry, with a first line saying "Imported thread".

Known tool labels: `claude`, `codex`, `vscode`, `copilot`, `chatgpt`, `cursor`, `gemini`. Any other name is shown as-is.

## 5. Searching later

- **Across all PRs on GitHub:** search `repo:<you>/<repo> is:pr "convo v1" <words>`. Comment text is indexed; the hidden marker matches every logged comment.
- **In git:** `git grep -i "<words>" -- '*.jsonl'`
- **By tool or role:** `jq -c 'select(.tool=="codex" and .role=="user")' conversations/*.jsonl`

## 6. Privacy

- On a **public** repo, PR comments are public. Only common secret formats are auto-redacted, and personal details are not. Use a private repo for private work, or review the log before opening the PR.
- To remove something after posting, edit or delete the PR comment on GitHub **and** the matching line in the log. Removing it from git history needs a history rewrite, so decide before merging.

## 7. Limits

- Only the assistant's **final** message per turn is captured. Text it wrote between tool calls is not.
- Messages from sub-agents are not captured.
- Long replies are split across several comments (GitHub caps a comment at 65,536 characters).
- If a PR is closed and a new one opened for the same branch, later comments go to the new PR. Earlier ones stay on the old one, and the log still has everything.
- It runs on macOS and Linux. On Windows use WSL: native Windows has no `fcntl`, so it runs without file locking and concurrent hooks can interleave.
