# History rewrite, 2026-09-25

On 2026-09-25 the repository's git history was rewritten to remove every coding-assistant conversation log,
at the operator's decision: the logs were not to be public. Removed from every commit on every branch and tag:

- `conversations/` (four branch logs)
- `experiments/E01-stentor-map/conversation.jsonl`
- `experiments/E02-local-negative-image/conversation.jsonl`

Nothing else changed: every other file in every commit is byte-for-byte as before. Conversation logging was
also switched off, and the kit that installed it no longer ships it.

## What this changes for the record

- **Every commit ID changed**, including the commits the milestone tags point to. The tags were moved to the
  rewritten commits. This departs from the protocol's rule that tags are never moved; it is logged in each
  experiment's `DEVIATIONS.md`.
- **The PR tag receipts quote the old commit IDs.** They remain valid for what they hash: `PREREG.md` and
  `ENV.lock` as committed at each tag, whose contents did not change. Use this table to match a receipt's
  commit to the current one:

| Tag | Commit in the receipts (old) | Commit now |
|---|---|---|
| `E01-stentor-map-closed` | `f10f6881f1d2` | `b873f62e7047` |
| `E01-stentor-map-interim-1` | `d2d19543f056` | `62f3ee0733ce` |
| `E01-stentor-map-prereg` | `ead2b9985806` | `ea88c8bab36a` |
| `E01-stentor-map-run` | `f10f6881f1d2` | `b873f62e7047` |
| `E02-local-negative-image-closed` | `a48db36bcc79` | `b5cd0c25f104` |
| `E02-local-negative-image-prereg` | `8e185cf3da38` | `0667c324fe42` |
| `E02-local-negative-image-run` | `a48db36bcc79` | `b5cd0c25f104` |
| `model-v0.1.0` | `7b14028f8114` | `0fcedbb8c2a8` |
| `model-v0.2.0` | `4217cd3c13c2` | `0d74262a2210` |

- Commit signatures from before the rewrite do not carry over to the rewritten commits.
- A private backup of the original history, logs included, is kept by the operator outside the repository.
