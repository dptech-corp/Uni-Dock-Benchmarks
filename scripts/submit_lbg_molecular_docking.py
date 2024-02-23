from pathlib import Path
import uuid
import os
import shutil
import json
import subprocess as sp


submit_dict = {
    "machine_type": "c16_m62_1 * NVIDIA T4",
    "command": "pip install wget && python test_molecular_docking.py --config_file config.json",
    "out_files": ["results_dir/results.json", "results_dir/results.csv", "results_dir/metrics.csv"],
    "platform": "ali",
    "on_demand": 1,
    "disk_size": 200,
    "image_name": "dptechnology/unidock_tools:1.0.0",
}

def submit_molecular_docking():
    tmpdir = Path(f"tmp_{uuid.uuid4().hex}")
    tmpdir.mkdir(parents=True, exist_ok=True)
    inputs_dir = tmpdir / "inputs"
    inputs_dir.mkdir()
    shutil.copytree(os.path.join(os.path.dirname(__file__), "utils"), inputs_dir / "utils")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "test_molecular_docking.py"), inputs_dir / "test_molecular_docking.py")
    run_config = {
        "rootdir": submit_dict["dataset_path"][0], 
        "savedir": "results_dir", 
        "round": 3,
        "srarch_mode_list": ["fast", "balance", "detail"],
    }
    with open(inputs_dir / "config.json", "w") as f:
        json.dump(run_config, f)

    with open(tmpdir / "submit.json", "w") as f:
        json.dump(submit_dict, f)
    cmd = f"lbg job submit -i {tmpdir / 'submit.json'} -p {inputs_dir}"
    resp = sp.run(cmd, shell=True, capture_output=True, encoding="utf-8")
    print(resp.stdout)
    if resp.returncode != 0:
        print(resp.stderr)

    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-pid", "--project_id", type=int, required=True)
    parser.add_argument("-j", "--job_name", type=str, default="test_virtual_screening")
    parser.add_argument("--dataset_path", type=str, nargs="+", default=["/bohr/uni-dock-testdata-tn4t/v4"])
    args = parser.parse_args()

    submit_dict["project_id"] = args.project_id
    submit_dict["job_name"] = args.job_name
    submit_dict["dataset_path"] = args.dataset_path

    submit_molecular_docking()