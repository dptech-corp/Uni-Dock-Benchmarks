from pathlib import Path
import uuid
import os
import shutil
import json
import subprocess as sp


scass_type_dict = {
    "t4": "c16_m62_1 * NVIDIA T4", # T4
    "2080ti": "c12_m46_1 * NVIDIA GPU B", # 2080Ti?
    "v100": "1 * NVIDIA V100_32g", # V100
    "3090": "c6_m64_1 * NVIDIA 3090", # 3090
    # A800/A100
    "4090": "c6_m60_1 * NVIDIA 4090", # 4090
    # L40
}


submit_dict = {
    "machine_type": "c16_m62_1 * NVIDIA T4",
    "command": "python test_virtual_screening.py --config_file config.json",
    "out_files": ["/tmp/results_dir/results.csv"],
    "platform": "ali",
    "on_demand": 1,
    "disk_size": 200,
    "image_name": "dptechnology/unidock_tools:sha-9a85585",
}

def submit_virtual_screening():
    tmpdir = Path(f"tmp_{uuid.uuid4().hex}")
    tmpdir.mkdir(parents=True, exist_ok=True)
    inputs_dir = tmpdir / "inputs"
    inputs_dir.mkdir()
    shutil.copytree(os.path.join(os.path.dirname(__file__), "utils"), inputs_dir / "utils")
    shutil.copyfile(os.path.join(os.path.dirname(__file__), "test_virtual_screening.py"), inputs_dir / "test_virtual_screening.py")
    run_config = {
        "rootdir": submit_dict["dataset_path"][0], 
        "savedir": "/tmp/results_dir", 
    }

    job_name = submit_dict["job_name"]
    for gpu_name, scass_type in scass_type_dict.items():
        for dataset_name in ["PPARG"]:
            for search_mode in ["fast", "balance"]:
                run_config["dataset_names"] = [dataset_name]
                run_config["search_mode_list"] = [search_mode]
                with open(inputs_dir / "config.json", "w") as f:
                    json.dump(run_config, f)
                submit_dict["machine_type"] = scass_type
                submit_dict["job_name"] = f'{job_name}_{gpu_name}_{dataset_name}_{search_mode}'
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
    parser.add_argument("--dataset_path", type=str, nargs="+", default=["/bohr/uni-dock-testdata-tn4t/v6"])
    args = parser.parse_args()

    submit_dict["project_id"] = args.project_id
    submit_dict["job_name"] = args.job_name
    submit_dict["dataset_path"] = args.dataset_path

    submit_virtual_screening()