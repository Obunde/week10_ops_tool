#!/usr/bin/env bash
# Driver for a live screen-recording of the week10_ops_tool demo.
# Run this from the repo root while recording (OBS / recordmydesktop) and read
# the matching narration from VIDEO_SCRIPT.md. It pauses between beats so you
# can talk.
#
#   ./demo.sh
#
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

pause() { printf '\n\033[2m— %s —  (press Enter)\033[0m' "$1"; read -r _; printf '\n'; }
run()   { printf '\033[1;36m$ %s\033[0m\n' "$*"; "$@"; }

clear
cat <<'BANNER'
============================================================
  week10_ops_tool — Data Freshness / SLA Monitor
  Product demo
============================================================
BANNER
pause "HOOK: state the problem (see VIDEO_SCRIPT.md 0:00-0:25)"

echo "The feeds we expect, and how fresh each must be:"
echo
sed -n '1,40p' feeds.example.yaml
pause "DEMO 1: seed the sample drop folder"

run python main.py --seed-samples
pause "DEMO 1: run the checks (expect BREACH, exit 1)"

set +e
run python main.py --dry-run
echo "   ^ exit code: $?"
set -e
pause "Read the four statuses: MISSING / EMPTY / LATE / OK"

echo "Now fix the feeds: refresh the stale file, add the missing one,"
echo "put real content in the empty one."
echo
run touch sample_data/inbox/inventory_2026-08-30.csv
run bash -c "printf 'id,amount\n1,9.99\n2,4.50\n' > sample_data/inbox/payments_2026-09-01.csv"
run bash -c "printf 'ts,url\n1,/home\n2,/pricing\n3,/docs\n' > sample_data/inbox/clickstream_2026-09-01.csv"
pause "DEMO 2: re-run (expect ALL OK, exit 0, no alert)"

set +e
run python main.py --dry-run
echo "   ^ exit code: $?"
set -e
pause "DEMO 3: launch the Streamlit UI (same core logic)"

echo "Starting Streamlit — Ctrl+C when you're done showing it."
echo
run python main.py --seed-samples   # back to the 3-breach state for the UI
streamlit run app.py

echo
echo "VALUE + CTA: see VIDEO_SCRIPT.md 2:10-3:00"
