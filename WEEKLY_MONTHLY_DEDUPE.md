# Weekly and Monthly Deduplication Workflow

This file is the repository entry point for the HealthTree TW weekly/monthly deduplication workflow.

## Data ownership

- `data/state.json`: source rotation and `site||URL` history.
- `data/published_urls.json`: exact published URL history and legacy title keywords.
- `data/published_topics.json`: structured cross-month topic index.
- `data/published_topic_aliases.json`: human-confirmed alternate titles for the same topic.
- `data/monthly_state.json`: monthly publication status only. Do not use it as an article database.

Do not delete old URLs, topics, weekly files, or source history after a monthly report is published.

## Candidate gate

Run this before accepting a weekly candidate:

```powershell
python tools\topic_dedupe.py check --title "Candidate title" --url "https://example.com/article"
```

Decision rules:

- `duplicate`: reject and select another candidate.
- `possible_duplicate`: hold for human review.
- `new`: continue with content/date/source validation.

Audit a completed weekly draft before rebuilding the index:

```powershell
python tools\topic_dedupe.py audit-weekly content\posts\YYYY-MM-DD-mm-weekly.md
```

## Update sequence

After a weekly draft is approved:

1. Update `data/state.json`.
2. Update `data/published_urls.json`.
3. Rebuild the structured topic index:

```powershell
python tools\topic_dedupe.py rebuild
```

4. Build Hugo and commit the weekly plus all changed data files together.

After a monthly report identifies a new alternate title for an existing topic:

1. Add the reviewed mapping to `data/published_topic_aliases.json`.
2. Run `rebuild` again.
3. Re-run `audit-weekly` against the rejected source weeklies as a regression test.

## Monthly publication safety

Use two commits:

1. Publish only the monthly report and verify its production URL and responsive layout.
2. Only after successful verification, set source weeklies to `draft = true` and update `data/monthly_state.json` in one commit.

Source weekly files remain in the repository. They are not deleted.

## Versioned operational notes

The detailed local notes are stored outside the repository:

- `C:\work2\tasks_version_backup\remote_weekly\weekly_report_local_backfill_notes_v3.md`
- `C:\work2\tasks_version_backup\remote_monthly\monthly_report_local_workflow_notes_v1.md`

Read the newest version before a backfill, weekly batch, or monthly publication.
