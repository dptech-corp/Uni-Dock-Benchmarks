#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

show_help() {
  cat << 'EOF'
Usage:
  # Single benchmark run
  ./run.sh single --savedir <DIR> --bin <BIN> --version <1|2> --type <molecular_docking|virtual_screening> [--device ID] [--seed SEED] [--nowater] [--dataset NAME]

  # Batch benchmark run (3 seeds/devices, nohup background)
  ./run.sh batch <savedir_basename> <device1> <device2> <device3> [--bin BIN] [--version 1|2] [--type molecular_docking|virtual_screening] [--nowater]

Examples:
  ./run.sh single --savedir results/dock_v2 --bin ud2 --version 2 --type molecular_docking --device 0 --seed 123
  ./run.sh single --savedir results/dock_v2_nowater --bin ud2 --version 2 --type molecular_docking --nowater
  ./run.sh batch results/dock_v2 0 1 2 --bin ud2 --version 2 --type molecular_docking
EOF
}

if [[ $# -lt 1 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  show_help
  exit 0
fi

MODE="$1"
shift

case "$MODE" in
  single)
    python "${ROOT_DIR}/scripts/run_test.py" --rootdir "${ROOT_DIR}" "$@"
    ;;
  batch)
    bash "${ROOT_DIR}/scripts/submit_udbench.sh" "$@"
    ;;
  *)
    echo "Error: unknown mode '${MODE}'. Use 'single' or 'batch'."
    echo
    show_help
    exit 1
    ;;
esac
