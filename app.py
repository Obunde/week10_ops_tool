"""week10_ops_tool — Streamlit UI for the Data Freshness / SLA Monitor.

Run with:  streamlit run app.py

Shares the exact same core logic as the CLI (``ops_tool`` package). This screen
lets you point at a config + drop folder, see the per-feed status, and send (or
preview) the alert.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from ops_tool.checker import check_all, has_breach
from ops_tool.config import ConfigError, load_config
from ops_tool.notifier import NotifyError, SmtpSettings, deliver
from ops_tool.report import breach_count, render_text, subject_line, summary_counts

load_dotenv()

st.set_page_config(page_title="week10_ops_tool — Data Freshness Monitor", page_icon="📡")
st.title("📡 Data Freshness / SLA Monitor")
st.caption("Checks expected data feeds in a drop folder against their freshness SLAs.")

default_config = os.getenv("FEEDS_CONFIG", "feeds.example.yaml")
default_drop = os.getenv("DROP_FOLDER", "./sample_data/inbox")

with st.sidebar:
    st.header("Configuration")
    config_path = st.text_input("Feeds config (YAML)", value=default_config)
    drop_folder = st.text_input("Drop folder", value=default_drop)
    dry_run = st.checkbox(
        "Dry run (never send email)",
        value=True,
        help="When unchecked, a breach sends email via the SMTP_* environment variables.",
    )
    run = st.button("Run checks", type="primary")

    smtp_ready = SmtpSettings.from_env() is not None
    st.markdown(f"**SMTP configured:** {'✅ yes' if smtp_ready else '❌ no — console fallback'}")

STATUS_COLORS = {
    "OK": "background-color: #1b5e20; color: white",
    "LATE": "background-color: #f9a825; color: black",
    "MISSING": "background-color: #b71c1c; color: white",
    "EMPTY": "background-color: #4a148c; color: white",
}

if not run:
    st.info("Set the config and drop folder in the sidebar, then click **Run checks**.")
    st.markdown(
        "First time? In a terminal run `python main.py --seed-samples` to create "
        "sample feed files, then come back and click **Run checks**."
    )
    st.stop()

try:
    config = load_config(config_path, drop_folder_override=drop_folder or None)
except ConfigError as exc:
    st.error(f"Config error: {exc}")
    st.stop()

if not config.drop_folder.is_dir():
    st.warning(
        f"Drop folder `{config.drop_folder}` does not exist — "
        "required feeds will show as MISSING."
    )

results = check_all(config)
counts = summary_counts(results)
breach = has_breach(results)

c1, c2, c3, c4 = st.columns(4)
c1.metric("OK", counts["OK"])
c2.metric("LATE", counts["LATE"])
c3.metric("MISSING", counts["MISSING"])
c4.metric("EMPTY", counts["EMPTY"])

df = pd.DataFrame(
    [
        {
            "Feed": r.name,
            "Status": r.status.value,
            "Detail": r.detail,
            "Pattern": r.spec.pattern,
            "SLA": r.spec.max_age_human,
            "Required": r.spec.required,
        }
        for r in results
    ]
)
st.dataframe(
    df.style.apply(
        lambda row: [STATUS_COLORS.get(row["Status"], "")] * len(row), axis=1
    ),
    width="stretch",
    hide_index=True,
)

subject = subject_line(results)
body = render_text(results, generated_at=datetime.now(timezone.utc))

if breach:
    st.error(f"BREACH — {breach_count(results)} feed(s) need attention.")
    try:
        channel = deliver(subject, body, dry_run=dry_run)
        if channel == "email":
            st.success("Alert email sent.")
        else:
            st.info("Alert not emailed (dry run or SMTP not configured). Preview below.")
    except NotifyError as exc:
        st.error(f"Email failed: {exc}")
else:
    st.success("All feeds within SLA — no alert needed.")

with st.expander("Alert / report preview", expanded=breach):
    st.code(f"Subject: {subject}\n\n{body}", language="text")
