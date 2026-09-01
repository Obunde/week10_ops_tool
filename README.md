# week10_ops_tool — Data Freshness / SLA Monitor

## What it does

Data and ops teams depend on files landing in a shared **drop folder** on a
schedule — nightly vendor extracts, hourly exports, backup dumps. When a feed
lands late, doesn't land at all, or lands truncated, downstream dashboards and
jobs silently go stale and nobody notices until a number looks wrong.

`week10_ops_tool` checks every expected feed in a drop folder against a declared
**freshness SLA** and raises an alert the moment something is off. For each feed
it finds the newest matching file and classifies it:

| Status    | Meaning                                                            |
|-----------|-------------------------------------------------------------------|
| `OK`      | a fresh, non-empty file exists (or an optional feed is absent)   |
| `LATE`    | newest file is older than the feed's `max_age`                   |
| `MISSING` | a required feed has no matching file                             |
| `EMPTY`   | newest file is smaller than the feed's `min_bytes` (truncated)   |

On any breach it writes a timestamped report (`.txt` / `.md` / `.json`) and
**emails an alert summary** via SMTP. If SMTP isn't configured, or you pass
`--dry-run`, the alert is printed to the console instead — so the tool always
runs end-to-end without credentials.

It ships as both a **CLI** (`main.py`, cron-friendly, meaningful exit codes) and
a **Streamlit UI** (`app.py`), sharing one core package (`ops_tool/`).

## Project layout

Everything sits at the repository root (the repo *is* the `week10_ops_tool`
directory — cloning it gives you a folder of that name).

```
week10_ops_tool/                 <- repo root == the tool directory
├── main.py                 CLI entrypoint (run, --dry-run, --seed-samples, --quiet)
├── app.py                  Streamlit UI  (streamlit run app.py)
├── ops_tool/
│   ├── config.py           load + validate feeds.yaml, parse "26h"/"90m"/"2d"
│   ├── checker.py          freshness classifier -> FeedResult list (pure logic)
│   ├── report.py           text / markdown / json renderers
│   └── notifier.py         SMTP send + console fallback (all creds from env)
├── feeds.example.yaml      sample SLA config (orders / inventory / clickstream / payments)
├── tests/test_checker.py   unit tests for the classifier + duration parser
├── conftest.py             puts the repo root on sys.path for pytest
├── requirements.txt
├── .env.example            the env vars to copy into .env
├── .gitignore              excludes .env, reports/, generated sample data
├── README.md               this file
├── PROMPTS.md              Part A: the Vibe Coding prompt log
│
│   # Part B / C course deliverables (also at the root so they are easy to find)
├── VIDEO_SCRIPT.md               3-minute product-demo narration with timings
├── demo.sh                       runs the demo sequence with pauses, for live recording
├── Week10_Product_Demo_Obunde.mp4  silent screencast (caption cards + real CLI output)
├── LINKEDIN_POST.md              promo post draft (text only, hashtags, repo link)
└── capstone_week10_update.md     Part C write-up (copy into the capstone repo root)
```

## Setup

Requires Python 3.10+.

```bash
git clone https://github.com/Obunde/week10_ops_tool.git
cd week10_ops_tool
python -m venv .venv && source .venv/bin/activate     # optional but recommended
pip install -r requirements.txt
cp .env.example .env                                   # then edit .env if you want real email
```

### Environment variables (`.env`)

| Variable        | Purpose                                                        |
|-----------------|---------------------------------------------------------------|
| `SMTP_HOST`     | SMTP server hostname. **Alert emails need this + FROM + TO.** |
| `SMTP_PORT`     | SMTP port (default `587`)                                     |
| `SMTP_USERNAME` | SMTP login (optional — omit for IP-allowlisted relays)       |
| `SMTP_PASSWORD` | SMTP password / app password (optional)                      |
| `SMTP_USE_TLS`  | `true` to STARTTLS (default `true`)                          |
| `ALERT_FROM`    | From address for the alert email                             |
| `ALERT_TO`      | Comma-separated recipient list                               |
| `DROP_FOLDER`   | Drop folder to scan (default `./sample_data/inbox`)          |
| `FEEDS_CONFIG`  | Path to the YAML config (default `./feeds.example.yaml`)     |
| `REPORT_DIR`    | Where reports are written (default `./reports`)              |

No secret is ever hardcoded — everything is read from the environment, loaded
from `.env` by `python-dotenv`. `.env` is gitignored.

## How to run it

### CLI

```bash
python main.py --seed-samples     # first time: create sample feed files
python main.py --dry-run          # run checks, print report + alert, no email
python main.py                    # run checks; email on breach if SMTP is set
python main.py --quiet            # output only when there's a breach (cron)
```

Exit codes: `0` all feeds OK · `1` at least one breach · `2` config error.

Example cron entry (every hour, quiet, email on breach):

```cron
0 * * * * cd /path/to/week10_ops_tool && /path/to/.venv/bin/python main.py --quiet
```

### Streamlit UI

```bash
streamlit run app.py
```

Set the config path and drop folder in the sidebar, click **Run checks**, and
you get the per-feed status table, the counts, and the alert preview. Leave
"Dry run" ticked to preview without sending.

## Defining your own SLAs

Edit `feeds.example.yaml` (or point `--config` / `FEEDS_CONFIG` at your own):

```yaml
drop_folder: ./sample_data/inbox
feeds:
  - name: orders
    pattern: "orders_*.csv"   # newest file matching this glob is the one checked
    max_age: 26h              # s | m | h | d
    min_bytes: 10             # smaller -> EMPTY
    required: true            # false -> "no file" is OK, not MISSING
```

## Testing it end-to-end

```bash
cd week10_ops_tool
pip install -r requirements.txt

# 1. Create sample feeds (orders=fresh, inventory=50h old, clickstream=empty, payments=absent)
python main.py --seed-samples

# 2. Run the checks — expect a report with OK / LATE / EMPTY / MISSING and exit code 1
python main.py --dry-run ; echo "exit: $?"

# 3. Make everything pass: refresh the stale files and add the missing one
touch sample_data/inbox/inventory_2026-08-30.csv
printf 'id,amount\n1,9.99\n2,4.50\n' > sample_data/inbox/payments_2026-09-01.csv
printf 'ts,url\n1,/home\n2,/pricing\n3,/docs\n' > sample_data/inbox/clickstream_2026-09-01.csv
python main.py --dry-run ; echo "exit: $?"   # expect ALL OK, exit code 0

# 4. Unit tests
pytest

# 5. UI
streamlit run app.py

# 6. (optional) real email: fill SMTP_* / ALERT_* in .env, then drop --dry-run
python main.py
```

## Course deliverables (Week 10)

| Part | Requirement | Where |
| --- | --- | --- |
| A | Working tool, runs without errors | this repo — `main.py` / `app.py`, `pytest` (22 tests) |
| A | Built with an AI assistant, prompts documented | [`PROMPTS.md`](PROMPTS.md) |
| A | No hardcoded secrets, `.env` based | [`.env.example`](.env.example) + `python-dotenv`; `.env` in [`.gitignore`](.gitignore) |
| B | 3-minute product demo video | [`Week10_Product_Demo_Obunde.mp4`](Week10_Product_Demo_Obunde.mp4) (silent screencast) + [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) narration; [`demo.sh`](demo.sh) drives a live recording |
| B | LinkedIn draft | [`LINKEDIN_POST.md`](LINKEDIN_POST.md) |
| C | Capstone integration write-up | [`capstone_week10_update.md`](capstone_week10_update.md) — copy to the capstone repo root |
