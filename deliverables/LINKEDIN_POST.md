# LinkedIn post — draft (text only)

---

Your data pipeline doesn't fail loudly. It fails quietly.

The nightly extract lands 6 hours late. The hourly export writes an empty file
because an upstream job died. A vendor feed just... doesn't show up. Nothing
crashes — the dashboards simply go stale, and someone finds out hours later when
a number looks wrong.

I used to catch this by hand: every morning, opening folders and eyeballing file
dates and sizes against a checklist. ~20 minutes a day, and it still missed the
silent failures.

So this week I vibe-coded a fix: **week10_ops_tool** — a data-freshness / SLA
monitor.

→ Declare each expected feed once in a YAML file: filename pattern, freshness SLA
  (e.g. "26h"), minimum size.
→ One command scans your landing folder and classifies every feed: OK / LATE /
  MISSING / EMPTY.
→ Timestamped reports in text, Markdown and JSON.
→ Emails an alert summary on any breach — with a console fallback so it runs
  with zero credentials.
→ Meaningful exit codes: drop it on cron and walk away.
→ CLI + a Streamlit UI over the same core. 22 tests. No hardcoded secrets —
  everything from environment variables.

The result: 20 minutes of manual checking every morning becomes a sub-second
automated run, and mean-time-to-detect a broken feed goes from hours to minutes.

Built almost entirely with an AI assistant — the repo includes a PROMPTS.md
documenting the actual prompts, including the one that mattered most: "ask me
clarifying questions first, then propose the architecture before writing code."

Code, setup, and a full test walkthrough:
https://github.com/Obunde/week10_ops-tool

If your team depends on scheduled data hand-offs, you can adopt this today.

#DataEngineering #DataQuality #Python #Automation #DevOps #Observability
#VibeCoding #AI #Streamlit #OpenSource #SRE

---

## Notes before posting

- Confirm the repo URL resolves publicly. If you rename the repo to
  `week10_ops_tool` (underscore, to match the assignment), update the link here.
- Optional: attach the demo video or a screenshot of the CLI breach output.
- Character count is well under LinkedIn's 3,000 limit.
