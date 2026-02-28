#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

show_help() {
  cat << 'EOF'
Usage:
  ./analyze.sh --runs <RUN_DIR_1> [RUN_DIR_2 ...] [--output <DIR>] [--name <PREFIX>] [--no-plot]

Description:
  Merge benchmark outputs (`metrics.csv` and `res.csv`) from multiple runs,
  then export merged CSV files and optional quick comparison figures.

Examples:
  ./analyze.sh --runs results/dock_v2_1 results/dock_v2_2 results/dock_v2_3 --output analysis/dock --name dock_v2
  ./analyze.sh --runs results/screen_v2 --output analysis/screen --name screen_v2 --no-plot
EOF
}

if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

python "${ROOT_DIR}/scripts/analyze_results.py" "$@"
