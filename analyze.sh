#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

show_help() {
  cat << 'EOF'
Usage:
  ./analyze.sh --runs <DIR> [<DIR> ...] [--name <LABEL> [<LABEL> ...]] [--output <DIR>] [--mode <MODE>] [--no-plot]

Description:
  Auto-discover run sub-directories (run_*) under one or more parent
  directories, merge metrics.csv from all runs, and produce a benchmark
  comparison figure (same style as show_udbench.ipynb's plot_benchmark).
  Multiple --runs directories are plotted side-by-side for cross-version
  comparison.

Options:
  --runs    One or more parent directories containing run_* sub-dirs (required).
  --name    Legend labels, one per --runs directory; the first is also used
            as the output file prefix (default: summary).
  --output  Output directory for merged table and plot (default: analysis).
  --mode    Benchmark mode: docking, screening, or auto (default: auto).
  --no-plot Disable plot generation and export the table only.

Examples:
  ./analyze.sh --runs results/ud2_v055_dock/ --name Uni-Dock2
  ./analyze.sh --runs results/ud2_v055_dock/ results/ud2_v060_dock/ --name UD2-v0.5.5 UD2-v0.6.0
  ./analyze.sh --runs results/ud2_v055_screen/ --name Uni-Dock2 --mode screening
EOF
}

if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

python "${ROOT_DIR}/scripts/analyze_results.py" "$@"
