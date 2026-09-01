# PROMPTS.md — Vibe Coding workflow

`week10_ops_tool` was built end-to-end with an AI assistant (**Claude / Claude
Code**). This file records the key prompts I gave, a one-line summary of what
each produced, and the follow-up prompts I used to fix or refine the result.

Tool type chosen: **Automation Script** — validates that expected data feeds land
in a drop folder on schedule and alerts (email, with console fallback) when a
feed is `MISSING`, `LATE`, or `EMPTY`.

---

## Entry 1 — Kickoff: requirements + "ask me first"

**Verbatim prompt:**

> I'm building a tool called `week10_ops_tool` for a course assignment.
> Requirements:
>
> 1. TOOL TYPE: [pick one — e.g., "An automation script that validates incoming
>    CSV data files against a schema and emails an alert summary when errors are
>    found" — be specific about the real operational problem it solves]
> 2. Build this as a working project with this structure: /week10_ops_tool with
>    main.py (or app.py if Streamlit), requirements.txt, .env.example
>    (placeholder keys only, no real secrets), .gitignore (must exclude .env),
>    README.md (what it does, setup steps, how to run it), PROMPTS.md (see
>    below).
> 3. SECURITY: No hardcoded secrets, API keys, or credentials anywhere in the
>    code. Load everything from environment variables via python-dotenv. Show me
>    the .env keys needed in .env.example.
> 4. As you generate each piece, ALSO append an entry to PROMPTS.md documenting:
>    the prompt I gave you, a one-line summary of what you generated, and any
>    follow-up prompt I used to fix/refine it. Keep updating this file as we
>    iterate — don't wait until the end.
> 5. Make sure the tool actually runs end-to-end without errors — walk me
>    through testing it before we call it done.
>
> Start by asking me clarifying questions about the exact operational problem and
> data/inputs involved, then propose the architecture before writing code.

**What it produced:** Four clarifying questions. My answers: **Data Freshness /
SLA monitor**, **CLI + Streamlit**, **SMTP email with console fallback**,
**local drop folder**. Claude then proposed the architecture — `ops_tool/` core
package (`config`, `checker`, `report`, `notifier`) + `main.py` CLI + `app.py`
Streamlit UI, a YAML config with `26h`-style durations, sample data seeded with
back-dated modification times, and exit codes `0`/`1`/`2`.

**Follow-up prompt:**

> ok lets build it

---

## Entry 2 — Full project generation

**Verbatim prompt:** `ok lets build it`

**What it produced:** The complete working project:

| File | What it does |
| --- | --- |
| `ops_tool/config.py` | Load + validate `feeds.yaml`; `parse_duration` for `s/m/h/d`; `FeedSpec` / `Config` dataclasses |
| `ops_tool/checker.py` | `check_feed` / `check_all` classify each feed `OK` / `LATE` / `MISSING` / `EMPTY` (EMPTY before LATE); pure logic |
| `ops_tool/report.py` | Text, Markdown and JSON renderers, worst-status-first ordering, `subject_line` |
| `ops_tool/notifier.py` | `SmtpSettings.from_env()` (no hardcoded creds), stdlib `smtplib` send, `deliver()` console fallback |
| `main.py` | argparse CLI: `--seed-samples`, `--dry-run`, `--quiet`, `--config`, `--drop-folder`, `--report-dir`; timestamped reports; exit `0/1/2` |
| `app.py` | Streamlit UI over the same core: status metrics, colour-coded table, alert preview / send |
| `feeds.example.yaml` | Four sample feeds chosen to demonstrate all four statuses |
| `tests/test_checker.py` | pytest cases for the classifier + duration parser |
| `requirements.txt`, `.env.example`, `.gitignore`, `README.md` | Project scaffolding; `.gitignore` excludes `.env`, `reports/`, generated sample data |

**Follow-up prompt:**

> Make sure the tool actually runs end-to-end without errors — walk me through
> testing it before we call it done.

---

## Entry 3 — End-to-end test run + fixes

**Verbatim prompt:** _(see the follow-up quoted in Entry 2)_

**What happened:** Ran the documented walkthrough on Python 3.13:

1. `python main.py --seed-samples` → 3 sample files created with back-dated
   mtimes; `payments_*.csv` deliberately absent.
2. `python main.py --dry-run` → report showed `MISSING` / `EMPTY` / `LATE` /
   `OK`, wrote `.txt` + `.md` + `.json` to `reports/`, printed the
   console-fallback alert, **exit code 1**.
3. Refreshed the stale/empty files and added `payments_*.csv` →
   `python main.py --dry-run` reported **ALL OK**, **exit code 0**.
4. `pytest` → **22 passed**.
5. Streamlit UI booted headless (HTTP 200) and was exercised with
   `streamlit.testing.v1.AppTest` — metrics, table, breach path and OK path all
   render with no exceptions.
6. SMTP send path verified against a local in-process SMTP sink —
   `notifier.deliver()` issued `MAIL FROM` / two `RCPT TO` / `DATA` with the
   correct subject and body.

**Fixes applied during testing:**

- `report.render_text`: dashed rules now span the widest rendered row, not just
  the header (cosmetic alignment).
- `app.py`: `use_container_width=True` → `width="stretch"` (Streamlit
  deprecation); bumped `streamlit>=1.50` in `requirements.txt`.
- `README.md`: corrected the "make everything pass" snippet so the regenerated
  `clickstream` file clears its 20-byte `min_bytes` threshold.

---

## Entry 4 — Fix `pytest` collection error

**Verbatim prompt:** _(pasted terminal output)_

> `ImportError while importing test module '.../tests/test_checker.py'` …
> `ModuleNotFoundError: No module named 'ops_tool'`
> `Interrupted: 1 error during collection`

**Diagnosis:** plain `pytest` adds the first parent dir *without* `__init__.py`
(`tests/`) to `sys.path`, not the project root, so `import ops_tool` fails.
`python -m pytest` had worked only because `-m` prepends the current directory.

**Fix:** added an empty `conftest.py` at the project root — pytest always adds
its directory to `sys.path`, so `pytest` and `python -m pytest` both work now.
Re-ran: **22 passed**.

---

## Entry 5 — Assignment compliance check

**Verbatim prompt:** _(the Week 10 brief — Part A technical tool, Part B demo
video + LinkedIn draft, Part C capstone update — followed by)_ "check if it has
satisfied the assignment requirements."

**What it produced:** A requirement-by-requirement audit against the rubric
(tool functionality, PROMPTS.md evidence, security, video, capstone), plus this
verbatim-prompt rewrite of `PROMPTS.md`, a `deliverables/VIDEO_SCRIPT.md`
(3-minute narration with timings), a `deliverables/LINKEDIN_POST.md` draft, and
a `capstone_week10_update.md` scaffold.

---

## Prompting techniques that worked

- **"Ask me clarifying questions first, then propose architecture before code."**
  Stopped the AI from guessing the problem domain and producing throwaway code.
- **Constraining the file layout up front** (exact filenames, `.env.example`,
  `.gitignore` must exclude `.env`) meant security best-practices were baked in
  from the first generation, not retrofitted.
- **Pasting raw terminal errors** (Entry 4) instead of describing them — the AI
  identified the pytest `sys.path` import-mode cause immediately.
- **Asking for an end-to-end test walkthrough** surfaced three real bugs that a
  code-only review would have missed.
