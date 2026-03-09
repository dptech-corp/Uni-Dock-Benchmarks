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
  ./run.sh <config.yaml>

  # Single benchmark run (legacy CLI)
  ./run.sh single --savedir <DIR> --bin <BIN> --version <1|2> --type <molecular_docking|virtual_screening> [--device ID] [--seed SEED] [--nowater] [--dataset NAME]

  # Batch benchmark run (legacy, 3 seeds/devices, nohup background)
  ./run.sh batch <savedir_basename> <device1> <device2> <device3> [--bin BIN] [--version 1|2] [--type molecular_docking|virtual_screening] [--nowater]

Examples:
  ./run.sh dump_config my_bench.yaml        # create config, then edit it
  ./run.sh my_bench.yaml                    # run the benchmark
  ./run.sh single --savedir results/dock_v2 --bin ud2 --version 2 --type molecular_docking --device 0 --seed 123
  ./run.sh batch results/dock_v2 0 1 2 --bin ud2 --version 2 --type molecular_docking
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
  dump_config)
    DEST="${1:-benchmark.yaml}"
    cp "${TEMPLATE_YAML}" "${DEST}"
    echo "Config template written to: ${DEST}"
    echo "Edit it, then run:  ./run.sh ${DEST}"
    ;;
  single)
    python "${ROOT_DIR}/scripts/run_test.py" --rootdir "${ROOT_DIR}" "$@"
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
