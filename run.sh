#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

TEMPLATE_YAML="${ROOT_DIR}/scripts/benchmark_template.yaml"

show_help() {
  cat << 'EOF'
Usage:
  # Generate a config file from the built-in template
  ./run.sh dump_config [output_path]        # default: ./benchmark.yaml

  # YAML-driven benchmark (recommended)
  ./run.sh <config.yaml> [--fg]

  # Stop a running benchmark (kills entire process tree)
  ./run.sh stop <PID>

  # Single benchmark run (legacy CLI)
  ./run.sh single --savedir <DIR> --bin <BIN> --version <1|2> --type <molecular_docking|virtual_screening> [--device ID] [--seed SEED] [--nowater] [--dataset NAME] [--fg]

  # Batch benchmark run (legacy, 3 seeds/devices, nohup background)
  ./run.sh batch <savedir_basename> <device1> <device2> <device3> [--bin BIN] [--version 1|2] [--type molecular_docking|virtual_screening] [--nowater]

Global options:
  --fg    Run in foreground (default: nohup background). Useful for debugging.

Examples:
  ./run.sh dump_config my_bench.yaml        # create config, then edit it
  ./run.sh my_bench.yaml                    # run in background (nohup)
  ./run.sh my_bench.yaml --fg               # run in foreground (for debugging)
  ./run.sh stop 12345                        # stop the running benchmark by PID
  ./run.sh single --savedir results/dock_v2 --bin ud2 --version 2 --type molecular_docking --device 0 --seed 123
  ./run.sh batch results/dock_v2 0 1 2 --bin ud2 --version 2 --type molecular_docking
EOF
}

# ---------------------------------------------------------------------------
# Helper: submit a command in background with nohup
# ---------------------------------------------------------------------------
submit_background() {
  local logfile="$1"
  local pidfile="$2"
  shift 2

  mkdir -p "$(dirname "$logfile")"

  nohup "$@" > "$logfile" 2>&1 &
  local pid=$!
  echo "$pid" > "$pidfile"

  echo "Task submitted in background (PID: $pid)"
  echo "  Log:      $logfile"
  echo "  PID file: $pidfile"
  echo "  Monitor:  tail -f $logfile"
}

# ---------------------------------------------------------------------------
# Arg parsing
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

FG=false
NEW_ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--fg" ]]; then
    FG=true
  else
    NEW_ARGS+=("$arg")
  fi
done
set -- "${NEW_ARGS[@]}"

MODE="$1"
shift

# ---------------------------------------------------------------------------
# YAML-driven mode: first argument ends with .yaml or .yml
# ---------------------------------------------------------------------------
if [[ "$MODE" == *.yaml ]] || [[ "$MODE" == *.yml ]]; then
  if [[ "$FG" == true ]]; then
    python "${ROOT_DIR}/scripts/run_bench.py" "$MODE" --rootdir "${ROOT_DIR}" "$@"
    exit $?
  fi

  SAVEDIR=$(python "${ROOT_DIR}/scripts/run_bench.py" "$MODE" --print-savedir)
  submit_background \
    "${SAVEDIR}/run_bench.out" \
    "${SAVEDIR}/run_bench.pid" \
    python "${ROOT_DIR}/scripts/run_bench.py" "$MODE" --rootdir "${ROOT_DIR}" "$@"
  exit 0
fi

case "$MODE" in
  stop)
    PID="${1:?Usage: ./run.sh stop <PID>}"
    if kill -0 "$PID" 2>/dev/null; then
      echo "Stopping process group (PID $PID) ..."
      kill -- -"$PID" 2>/dev/null || kill "$PID" 2>/dev/null
      echo "Done. All processes terminated."
    else
      echo "Process $PID is not running (already finished or killed)."
    fi
    exit 0
    ;;
  dump_config)
    DEST="${1:-benchmark.yaml}"
    cp "${TEMPLATE_YAML}" "${DEST}"
    echo "Config template written to: ${DEST}"
    echo "Edit it, then run:  ./run.sh ${DEST}"
    ;;
  single)
    SAVEDIR=""
    ARGS=("$@")
    for ((i=0; i<${#ARGS[@]}; i++)); do
      if [[ "${ARGS[$i]}" == "--savedir" ]] && [[ $((i+1)) -lt ${#ARGS[@]} ]]; then
        SAVEDIR="${ARGS[$((i+1))]}"
        break
      fi
    done
    if [[ -z "$SAVEDIR" ]]; then
      echo "Error: --savedir is required for single mode"
      exit 1
    fi

    if [[ "$FG" == true ]]; then
      python "${ROOT_DIR}/scripts/run_test.py" --rootdir "${ROOT_DIR}" "$@"
    else
      submit_background \
        "${SAVEDIR}/run_single.out" \
        "${SAVEDIR}/run_single.pid" \
        python "${ROOT_DIR}/scripts/run_test.py" --rootdir "${ROOT_DIR}" "$@"
    fi
    ;;
  batch)
    bash "${ROOT_DIR}/scripts/submit_udbench.sh" "$@"
    ;;
  *)
    echo "Error: unknown mode '${MODE}'. Use a .yaml config file, 'dump_config', 'single', or 'batch'."
    echo
    show_help
    exit 1
    ;;
esac
