#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANALYZE="${SCRIPT_DIR}/scripts/analyze_results.py"
RESULTS_DIR="${SCRIPT_DIR}/results"

show_help() {
  cat << 'EOF'
Usage:
  ./analyze.sh --methods <M1> <M2> [...] --labels <L1> <L2> [...] --output <DIR> [--no-date]

Description:
  Generate all benchmark plots (dock water, dock nowater, screening, combined)
  by auto-discovering result directories following the naming convention:
    results/<METHOD>_dock_water/
    results/<METHOD>_dock_nowater/
    results/<METHOD>_screen/

Options:
  --methods   Result directory prefixes under results/ (required).
  --labels    Legend labels, one per method (required).
  --output    Output directory for plots and merged CSVs (required).
  --no-date   Hide date stamp in plot titles.

Example:
  ./analyze.sh --methods ud1_v1.1.3 ud2_api_0.6.1 \
               --labels "Uni-Dock1_v1.1.3" "Uni-Dock2_v0.6.1" \
               --output analysis/0.6.1_vs_1.1.3 --no-date
EOF
}

METHODS=()
LABELS=()
OUTPUT=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    --methods) shift; while [[ $# -gt 0 ]] && [[ "$1" != --* ]]; do METHODS+=("$1"); shift; done ;;
    --labels)  shift; while [[ $# -gt 0 ]] && [[ "$1" != --* ]]; do LABELS+=("$1");  shift; done ;;
    --output)  OUTPUT="$2"; shift 2 ;;
    --no-date) EXTRA_ARGS+=("--no-date"); shift ;;
    *) echo "Unknown option: $1"; show_help; exit 1 ;;
  esac
done

if [[ ${#METHODS[@]} -eq 0 ]] || [[ ${#LABELS[@]} -eq 0 ]] || [[ -z "$OUTPUT" ]]; then
  echo "Error: --methods, --labels, and --output are all required."
  show_help
  exit 1
fi

if [[ ${#METHODS[@]} -ne ${#LABELS[@]} ]]; then
  echo "Error: number of --methods (${#METHODS[@]}) must match --labels (${#LABELS[@]})."
  exit 1
fi

DOCK_WATER=()
DOCK_NOWATER=()
SCREEN=()
for m in "${METHODS[@]}"; do
  DOCK_WATER+=("${RESULTS_DIR}/${m}_dock_water")
  DOCK_NOWATER+=("${RESULTS_DIR}/${m}_dock_nowater")
  SCREEN+=("${RESULTS_DIR}/${m}_screen")
done

echo "=== Generating dock water plot ==="
python "$ANALYZE" --runs "${DOCK_WATER[@]}" --name water "${LABELS[@]}" \
  --output "$OUTPUT" --mode docking "${EXTRA_ARGS[@]}"

echo "=== Generating dock nowater plot ==="
python "$ANALYZE" --runs "${DOCK_NOWATER[@]}" --name nowater "${LABELS[@]}" \
  --output "$OUTPUT" --mode docking "${EXTRA_ARGS[@]}"

echo "=== Generating screening plot ==="
python "$ANALYZE" --runs "${SCREEN[@]}" --name screen "${LABELS[@]}" \
  --output "$OUTPUT" --mode screening "${EXTRA_ARGS[@]}"

echo "=== Generating combined plot ==="
python "$ANALYZE" \
  --runs "${DOCK_WATER[@]}" "${DOCK_NOWATER[@]}" "${SCREEN[@]}" \
  --name all "${LABELS[@]}" \
  --output "$OUTPUT" --mode all "${EXTRA_ARGS[@]}"

echo "=== Done. Output: $OUTPUT ==="
