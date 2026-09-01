# Capstone (flowgard) — Week 10 Update

> Move this file to the **root of the flowgard repository** and commit it there.
> A few `[CONFIRM]` markers remain for things only you can verify (whether the
> code is committed yet, exact paths). Everything else is written to match
> flowgard's actual architecture.

## Context

**flowgard** — multi-tenant predictive-maintenance platform for fluid-transport
pipeline infrastructure (pumps/pipelines), with **KPC (Kenya Pipeline Company)**
as the anchor tenant (13 stations + pump fleet). FastAPI · SQLAlchemy 2.0 ·
Alembic · PostgreSQL · Pydantic v2 · pytest, managed with `uv`. Current state:
structural scaffolding — modules, base models, service stubs, migrations and KPC
seed data are in place; ML models and the Flowgard math are being filled in
module by module.

## Vibe-coded component added this week

**`week10_ops_tool` — an ingestion-freshness / SLA monitor**, built end-to-end
with an AI assistant (Claude Code). Standalone repo:
https://github.com/Obunde/week10_ops-tool

It declares each expected data feed in a YAML file (filename pattern, freshness
SLA like `26h`, minimum size, required flag), scans a landing folder, and
classifies every feed `OK` / `LATE` / `MISSING` / `EMPTY` — with `EMPTY`
deliberately outranking `LATE`, because a present-but-truncated file is the
failure mode manual checks always miss. It writes text/Markdown/JSON reports,
emails an alert summary on any breach (console fallback when SMTP isn't set), and
returns meaningful exit codes so it runs under cron. CLI + a Streamlit UI over
one shared core. 22 tests. No hardcoded secrets — every credential comes from
`.env` via `python-dotenv`.

### Why flowgard needs this

flowgard's whole value chain is downstream of ETL ingestion:

```
simulator / SCADA ─┐
weather API        ├─▶ etl/bronze ─▶ etl/silver ─▶ etl/gold ─▶ feature_engineering
regional risk data ┘   (raw landing)  (sensor_reading …)  (rolling windows)   │
                                                                              ▼
                                          flowgard_engine ▶ prediction / rul / explainability
```

If a tenant's sensor feed stops landing, nothing errors — `feature_engineering`
just builds vectors from stale Gold rows, and `prediction` emits a 7-day risk
score and `rul` an RUL estimate that look current but aren't. For a maintenance
platform, a **silently stale risk score is worse than an outage**: someone
trusts it.

flowgard already has an `alert/` module, but that's for *pump-health* thresholds
(Health Deviation Index, vibration, etc.). This monitor is complementary — it
watches **data-pipeline health**: is each tenant's ingestion actually fresh?

### Where it goes in the repo

`ops/freshness_monitor/` — a **top-level sibling of `app/`**, not an `app/<module>/`
slice. This is deliberate and consistent with flowgard's architecture rules: the
monitor has no HTTP surface, no business entity, and doesn't follow the
routes → services → models direction, so it does not belong under `app/`. It's
operational tooling, like `scripts/` and `migrations/`. `[CONFIRM: create the
folder and commit the adapted tool, or vendor the standalone repo as a
submodule.]`

Run modes:

- **cron**, alongside the ETL schedule — `uv run python -m ops.freshness_monitor --quiet`
- **pre-flight check** before a modelling run — non-zero exit aborts the batch
  so `prediction` / `rul` never execute on stale input `[CONFIRM: wire into
  whatever kicks off the pipeline]`

---

## 1. How did AI accelerate my Capstone development this week?

Two ways.

**A complete auxiliary tool in hours, not a day.** Hand-building the monitor —
argparse, YAML validation, the freshness classifier, three report formats, an
SMTP client with a safe fallback, a Streamlit UI, tests — would have been a full
day I couldn't spare from flowgard's core modules. With AI it was a few hours of
guided iteration, and the time went into *decisions* (what "late" means, whether
empty outranks late, keeping it runnable with zero credentials) rather than
boilerplate. flowgard gets a real operational capability for the cost of an
afternoon.

**Faster iteration inside flowgard's constraints.** Because flowgard's
`README`/architecture rules are explicit — one-way dependency direction,
`tenant_id` on every scoped table, one `Settings` object, one engine — I can
paste those rules as context and have the AI generate module code that already
respects them (correct `TenantScopedMixin` usage, `services.py` taking
`tenant_id` as a required arg and filtering every query), instead of writing a
generic version and reworking it.

Concrete AI wins this week:

- Generated the monitor's scaffold, `.env.example`, `.gitignore` and tests
  correctly on the first pass.
- Diagnosed a `pytest` import failure from the raw traceback (`tests/` on
  `sys.path` instead of the project root) and fixed it with a root `conftest.py`
  — the same import-mode gotcha applies to flowgard's `tests/` tree.
- Drove an end-to-end test walkthrough (CLI, Streamlit via `AppTest`, and a
  local SMTP sink to prove the email path), which caught three real bugs.

## 2. What specific feature did I build using Vibe Coding?

The **feed-freshness classifier and alerting flow** in `week10_ops_tool`: given
a declarative list of expected feeds, locate the newest artefact per feed,
classify it `OK` / `LATE` / `MISSING` / `EMPTY`, render a report, and send an
alert summary on any breach with a credential-free console fallback. Pure,
tested logic (`week10_ops_tool/checker.py`), decoupled from both the input source and
the delivery channel.

**The flowgard adaptation I started from it:** a DB-backed variant of the same
classifier. flowgard's feeds don't land as files — ETL writes them as rows in
`sensor_reading` / `weather_reading` / `regional_risk_score`. So the flowgard
version keeps the classifier and swaps the source: per tenant, per source,
`SELECT max(reading_ts) …` compared against a freshness SLA read from the
tenant's own config (`app/tenant/` already stores per-tenant `thresholds`). Same
four statuses, same alert flow, tenant-scoped like every other query in the
codebase. `[CONFIRM: how far you took this — stub, working query, or wired in.]`

## 3. One prompting challenge and how I overcame it

**Challenge:** an AI asked for "a freshness monitor" defaults to a flat script —
file globbing, `print`, logic and I/O tangled together. That's the opposite of
what flowgard needs: the check has to be tenant-scoped, source-agnostic (files
now, Postgres rows in the Capstone), and channel-agnostic, or it can't be reused
inside `app/`.

**How I overcame it:** I stopped prompting for "a tool" and started prompting
for *seams*. Specifically I required (a) the classifier to be a pure function
over a list of "feed results" with no knowledge of where they came from, and (b)
delivery to sit behind a single `deliver()` function with the console fallback
built in. I also opened the whole build by instructing the AI to **ask
clarifying questions and propose an architecture before writing any code** — that
one line turned the first response into four design questions instead of 300
lines I'd have to unpick. The result: porting to flowgard's DB source is a new
20-line adapter feeding the *same* `checker.py`, not a rewrite.

A related lesson carried into flowgard module work: paste the architecture rules
as context up front. When I don't, the AI writes a `models.py` that imports a
service or a `services.py` that forgets `tenant_id` — both of which violate
flowgard's stated dependency direction and tenancy rule and cost a review cycle.

---

## Status

- [ ] `week10_ops_tool` committed into flowgard at `ops/freshness_monitor/` (or vendored as a submodule)
- [ ] DB-backed classifier variant: `[CONFIRM state]`
- [ ] Cron / pre-flight integration point wired: `[CONFIRM script]`
- [ ] `.env.example` updated in flowgard if the monitor adds any keys; real `.env` still gitignored
- [ ] This file committed at the flowgard repo root as `capstone_week10_update.md`
