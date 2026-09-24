# EXPERIMENT_PR_LOG.md — Branch, PR, and conversation record per experiment

**Applies to:** every LLM coding session and human contributor.
**Depends on:** `.agents/protocols/CONVERSATIONS.md` + `.agents/tools/convo-log` (conversation capture) and, if used,
`PREREG_PROTOCOL.md` (experiment IDs, tags). This document only defines *where* the record
goes and *what* gets posted; it does not define preregistration itself.
**Installed by:** the KIT Adaptive Preregistration `experiment-pr-log` module, which also adds the one-line rule to `AGENTS.md`.

---

## 1. Rules

Every experiment gets one branch and one draft PR, so the agent chat behind each version lands
on the PR for that version and in git beside the results.

| Rule | Detail |
|---|---|
| Branch per experiment | `experiment/<EID>` off `main`. Model changes go on `model/<topic>` branches, not experiment branches. |
| Draft PR at start | First action on the branch: `git commit --allow-empty -m "start <EID>"; git push -u origin HEAD; gh pr create --draft --title "<EID>: <title>" --body "Preregistered experiment. See experiments/<EID>/PREREG.md"`. Until the PR exists, convo-log queues; nothing is lost. |
| Log location | `experiments/<EID>/conversation.jsonl`, committed with the experiment. The module routes it automatically via `.agents/config/convo-log.d/experiment-pr-log.json`. |
| Prereg receipt on the PR | Tag `<EID>-prereg` with `.agents/tools/tag` (§2), which posts the receipt as a PR comment straight away. GitHub's comment timestamp is a third-party clock, which local git dates are not. This is the cheap external timestamp `PREREG_PROTOCOL.md` §2 asks for. |
| Interim and run receipts | Same after each `-interim-N`, `-run`, `-closed` tag. The PR then shows the ordering prereg → interim → run → closed with server-side times, independent of the log. |
| Deviations echo | Each new row in `DEVIATIONS.md` is also posted as a PR comment by the same hook, so the chat, the deviation, and the commit are adjacent on one page. |
| PR stays open until closed | Merge only after `<EID>-closed`. A FAIL is still merged: the closed folder is the record. Squash-merging is forbidden (it destroys the tag→commit mapping); use merge commits. |
| Never edit logs | As in CONVERSATIONS.md. Redaction happens before write; anything else is a history rewrite and is out. |

## 2. Tools (installed in `.agents/`)

| File | What it does |
|---|---|
| `.agents/tools/tag <tag> "<message>"` | `git tag -a` with a dated message, then posts the receipt. Agents use this, **never bare `git tag`**, for experiment tags. |
| `.agents/tools/prereg-receipt <tag>` | Posts a tag receipt to the branch's PR: commit, tag date, and sha256 of `experiments/<EID>/PREREG.md` and `ENV.lock`. GitHub's comment time is the third-party clock. |
| `.agents/tools/prereg-status` | Prints one line of context (branch, EID, tags present, whether `PREREG.md` is FROZEN). Claude Code runs it on every prompt via the `UserPromptSubmit` hook. |

## 3. Commit guard (`.agents/githooks/pre-commit`)

Enable once per clone with `git config core.hooksPath .agents/githooks`. This replaces `.git/hooks` for the repo, so move any existing hooks into the kit first.

It refuses to commit:
- run outputs (`experiments/<EID>/outputs/*`, `RESULTS.md`) for an experiment that has no `<EID>-prereg` tag;
- any change to `experiments/<EID>/PREREG.md` after `<EID>-prereg` exists. Log the change in `DEVIATIONS.md` instead.

## 4. Hooks

The module merges a Claude Code `UserPromptSubmit` hook running `.agents/tools/prereg-status` into `.claude/settings.json`, next to the convo-log hooks. Tools without hooks should run it at the start of a session on an `experiment/*` branch.

---

## 5. Using this without PREREG_PROTOCOL.md

Replace `<EID>` with any work-unit slug and drop the tag names you don't use. The branch→PR→log
mapping and `.agents/tools/tag` + receipt still work. The commit guard assumes `-prereg` tags (it blocks
run outputs without one), so leave it off if you don't preregister.
