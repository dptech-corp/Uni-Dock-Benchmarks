#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

show_help() {
  cat << 'EOF'
Usage:
  # YAML-driven benchmark (recommended)
  ./run.sh <config.yaml>

  # Single benchmark run (legacy CLI)
  ./run.sh single --savedir <DIR> --bin <BIN> --version <1|2> --type <molecular_docking|virtual_screening> [--device ID] [--seed SEED] [--nowater] [--dataset NAME]

  # Batch benchmark run (legacy, 3 seeds/devices, nohup background)
  ./run.sh batch <savedir_basename> <device1> <device2> <device3> [--bin BIN] [--version 1|2] [--type molecular_docking|virtual_screening] [--nowater]

Examples:
  ./run.sh benchmark.yaml
  ./run.sh single --savedir results/dock_v2 --bin ud2 --version 2 --type molecular_docking --device 0 --seed 123
  ./run.sh batch results/dock_v2 0 1 2 --bin ud2 --version 2 --type molecular_docking

See scripts/benchmark_template.yaml for the YAML config format.
EOF
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

MODE="$1"
shift

# YAML-driven mode: first argument ends with .yaml or .yml
if [[ "$MODE" == *.yaml ]] || [[ "$MODE" == *.yml ]]; then
  python "${ROOT_DIR}/scripts/run_bench.py" "$MODE" --rootdir "${ROOT_DIR}" "$@"
  exit $?
fi

case "$MODE" in
  single)
    python "${ROOT_DIR}/scripts/run_test.py" --rootdir "${ROOT_DIR}" "$@"
    ;;
  batch)
    bash "${ROOT_DIR}/scripts/submit_udbench.sh" "$@"
    ;;
  *)
    echo "Error: unknown mode '${MODE}'. Use a .yaml config file, 'single', or 'batch'."
    echo
    show_help
    exit 1
    ;;
esac
