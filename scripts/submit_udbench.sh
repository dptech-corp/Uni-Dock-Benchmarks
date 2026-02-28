#!/usr/bin/env bash
set -euo pipefail

# Show help information
show_help() {
  cat << EOF
Usage: bash scripts/submit_udbench.sh <savedir_basename> <device1> <device2> <device3> [options]

Description:
  Submit 3 benchmark test tasks in batch, each using different GPU devices and seeds.
  Tasks run in the background (nohup) and will not block.

Required arguments:
  <savedir_basename>    Base name for the output directory, will automatically append _1, _2, _3 suffixes
  <device1>             GPU device ID for the first task (e.g., 1 4 5 or 0 3 7)
  <device2>             GPU device ID for the second task
  <device3>             GPU device ID for the third task

Optional arguments:
  --bin BIN             Binary file name (default: ud2)
  --version VER         Uni-Dock version, 1 or 2 (default: 2)
  --type TYPE           Task type: molecular_docking or virtual_screening (default: molecular_docking)
  --nowater             Use receptor without water (only for molecular_docking)
  -h, --help            Show this help message

Fixed settings:
  seed:                 Tasks 1/2/3 use 121, 122, 123 respectively
  output directory:    <savedir_basename>/
  savedir:             <savedir_basename>/<savedir_basename>_1, <savedir_basename>/<savedir_basename>_2, <savedir_basename>/<savedir_basename>_3
  output files:        <savedir_basename>/<savedir_basename>_1.out, <savedir_basename>/<savedir_basename>_2.out, <savedir_basename>/<savedir_basename>_3.out
  PID files:           <savedir_basename>/<savedir_basename>_1.pid, <savedir_basename>/<savedir_basename>_2.pid, <savedir_basename>/<savedir_basename>_3.pid

Examples:
  # Basic usage (with default values)
  bash scripts/submit_udbench.sh res2_0.4.4.1_dock 0 1 2

  # Specify all parameters
  bash scripts/submit_udbench.sh res2_0.4.4.1_dock 0 1 2 --bin ud2_0.4.4.1 --version 2 --type molecular_docking

  # Use --nowater parameter
  bash scripts/submit_udbench.sh res2_0.4.4.1_dock 0 1 2 --bin ud2_0.4.4.1 --version 2 --type molecular_docking --nowater

  # Virtual screening task
  bash scripts/submit_udbench.sh res_vs 0 1 2 --bin ud2_v0.2 --version 2 --type virtual_screening

EOF
}

# Check help argument
if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

if [[ $# -lt 4 ]]; then
  echo "Error: Insufficient arguments"
  echo ""
  show_help
  exit 1
fi

BASE_SAVEDIR="$1"
DEVICES=("$2" "$3" "$4")

# Default values for optional parameters
BIN="ud2"
VERSION="2"
TYPE="molecular_docking"
NOWATER=""

# Parse optional parameters
shift 4
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bin)
      BIN="$2"; shift 2
      ;;
    --version)
      VERSION="$2"; shift 2
      ;;
    --type)
      TYPE="$2"; shift 2
      ;;
    --nowater)
      NOWATER="--nowater"; shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Error: Unknown argument: $1"
      echo ""
      show_help
      exit 1
      ;;
  esac
done

# Fixed three seeds
SEEDS=(121 122 123)

# Working root directory (repo root inferred from this script path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Check if entry script exists
ENTRY="${ROOT}/scripts/run_test.py"
if [[ ! -f "$ENTRY" ]]; then
  echo "Error: Entry script not found: $ENTRY"
  exit 1
fi

# Create output directory
mkdir -p "${BASE_SAVEDIR}"

# Submit 3 tasks sequentially
PIDS=()
for i in 0 1 2; do
  SAVEDIR_NAME="${BASE_SAVEDIR}_$((i+1))"
  SAVEDIR="${BASE_SAVEDIR}/${SAVEDIR_NAME}"
  DEVICE="${DEVICES[$i]}"
  SEED="${SEEDS[$i]}"
  OUTFILE="${BASE_SAVEDIR}/${SAVEDIR_NAME}.out"
  PIDFILE="${BASE_SAVEDIR}/${SAVEDIR_NAME}.pid"

  # Build command
  CMD=(python "$ENTRY" --rootdir "$ROOT" --savedir "$SAVEDIR" --bin "$BIN" --version "$VERSION" --type "$TYPE" --device "$DEVICE" --seed "$SEED")
  if [[ -n "$NOWATER" ]]; then
    CMD+=("$NOWATER")
  fi

  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Submitting task $((i+1)):"
  echo "  savedir: $SAVEDIR"
  echo "  device: $DEVICE"
  echo "  seed: $SEED"
  echo "  output file: $OUTFILE"
  echo "  command: nohup ${CMD[*]} > ${OUTFILE} 2>&1 &"
  
  # Submit task and get PID
  nohup "${CMD[@]}" > "${OUTFILE}" 2>&1 &
  TASK_PID=$!
  PIDS+=($TASK_PID)
  
  # Save PID to file
  echo "$TASK_PID" > "${PIDFILE}"
  
  echo "  PID: $TASK_PID (saved to ${PIDFILE})"
  echo ""
  
  sleep 1  # Brief delay to avoid starting too many processes simultaneously
done

echo "=========================================="
echo "Submitted 3 tasks (running in background, non-blocking):"
echo "  output directory: ${BASE_SAVEDIR}/"
echo "  savedir: ${BASE_SAVEDIR}/${BASE_SAVEDIR}_1, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_2, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_3"
echo "  devices: ${DEVICES[*]}"
echo "  seeds: ${SEEDS[*]}"
echo "  PIDs: ${PIDS[*]}"
echo "  output files: ${BASE_SAVEDIR}/${BASE_SAVEDIR}_1.out, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_2.out, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_3.out"
echo "  PID files: ${BASE_SAVEDIR}/${BASE_SAVEDIR}_1.pid, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_2.pid, ${BASE_SAVEDIR}/${BASE_SAVEDIR}_3.pid"
echo "=========================================="

