# Week10_Product_Demo_Obunde.mp4 — 3-minute script

**Format:** screen-share with voiceover. Target 2:55–3:00.
**Before recording:** terminal open in `week10_ops_tool/`, virtualenv active,
`python main.py --seed-samples` already run so the demo state has 3 breaches.
Have a second terminal tab and the Streamlit app ready to launch.

---

## 0:00 – 0:25 · Hook (the operational problem)

> "Every data team runs on files that are supposed to show up on a schedule —
> the nightly orders extract, the hourly clickstream drop, the vendor payments
> file. When one of them is late, missing, or lands half-written, nothing
> crashes. The dashboards just quietly go stale, and you find out hours later
> when a number looks wrong and someone asks why.
>
> Today I check this by hand every morning — opening folders, eyeballing file
> dates and sizes against a mental checklist. It takes about 20 minutes and it
> still misses the silent failures. So I built `week10_ops_tool` to do it in
> under a second."

## 0:25 – 1:35 · Demo (tool in action)

**Show `feeds.example.yaml` briefly (5s):**

> "I declare each expected feed once: a filename pattern, how fresh it has to be
> — 26 hours here — and a minimum size so I catch truncated files."

**Run the CLI:**

```bash
python main.py --dry-run
```

> "One command. It finds the newest file for each feed and classifies it.
> `orders` is OK — two hours old. `inventory` is LATE — last modified two days
> ago, past its 26-hour SLA. `clickstream` is EMPTY — zero bytes, so the job
> that writes it failed silently. And `payments` is MISSING entirely.
>
> It writes a timestamped report in text, Markdown and JSON, and because there's
> a breach it builds an alert email. I don't have SMTP configured in this demo,
> so it prints the alert instead — in production this lands in the on-call
> inbox. Exit code 1, so if this is running under cron, a failure is
> unambiguous."

**Fix the feeds, re-run:**

```bash
touch sample_data/inbox/inventory_2026-08-30.csv
printf 'id,amount\n1,9.99\n2,4.50\n' > sample_data/inbox/payments_2026-09-01.csv
printf 'ts,url\n1,/home\n2,/pricing\n3,/docs\n' > sample_data/inbox/clickstream_2026-09-01.csv
python main.py --dry-run
```

> "Now everything's within SLA — ALL OK, exit code 0, no alert sent. It only
> ever bothers you when something is actually wrong."

## 1:35 – 2:10 · Demo (Streamlit UI)

```bash
streamlit run app.py
```

> "Same core logic, with a UI for anyone who doesn't live in a terminal. Point
> it at the config and the drop folder, hit Run checks — status counts up top,
> a colour-coded row per feed, and the exact alert that would go out. 'Dry run'
> stays on until you're ready to send for real."

*(Toggle one feed back to broken on disk, re-run in the UI to show a red BREACH
row.)*

## 2:10 – 2:40 · Value (quantify it)

> "Concretely: this replaces about 20 minutes of manual folder-checking every
> morning with a sub-second automated run I schedule with one cron line. More
> importantly, mean time to detect a broken feed drops from hours — whenever
> someone happens to notice a bad number — to minutes, the next cron tick. And
> the failure mode that manual checks always miss, a file that's present but
> empty, is a first-class check here.
>
> It's about 300 lines, no external services beyond SMTP, 22 tests, and every
> credential comes from an environment variable — nothing hardcoded."

## 2:40 – 3:00 · Call to action

> "Any team that depends on scheduled data hand-offs can drop this in today: add
> your feeds to one YAML file, point it at your landing folder, put it on cron.
> You stop being the monitoring system. The code's on GitHub —
> github.com/Obunde/week10_ops-tool — README has setup and a full test
> walkthrough. Thanks for watching."

---

### Recording checklist

- [ ] Terminal font large enough to read at 1080p
- [ ] `--seed-samples` run before hitting record (demo starts in the 3-breach state)
- [ ] Second tab ready for `streamlit run app.py`
- [ ] Close noisy notifications
- [ ] Export as `Week10_Product_Demo_Obunde.mp4`, check length ≤ 3:00
