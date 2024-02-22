from pathlib import Path
import uuid
import os
import shutil
import json
import subprocess as sp


scass_type = "c16_m62_1 * NVIDIA T4"
job_name = "test_molecular_docking_unidock1.0_t4"

submit_dict = {
    "project_id": 11053,
    "dataset_path": ["/bohr/uni-dock-testdata-tn4t/v2"],
    "command": "python test_molecular_docking.py --config_file config.json",
    "out_files": ["results_dir/results.json", "results_dir/results.csv", "results_dir/metrics.csv"],
    "platform": "ali",
    "on_demand": 1,
    "disk_size": 200,
    "image_name": "registry.dp.tech/dp/vina_pipeline:0.1.10",
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
    }
    with open(inputs_dir / "config.json", "w") as f:
        json.dump(run_config, f)
    
    submit_dict["machine_type"] = scass_type
    submit_dict["job_name"] = job_name
    with open(tmpdir / "submit.json", "w") as f:
        json.dump(submit_dict, f)
    cmd = f"lbg job submit -i {tmpdir / 'submit.json'} -p {inputs_dir}"
    resp = sp.run(cmd, shell=True, capture_output=True, encoding="utf-8")
    print(resp.stdout)
    if resp.returncode != 0:
        print(resp.stderr)

    shutil.rmtree(tmpdir)


if __name__ == "__main__":
    submit_molecular_docking()