from __future__ import annotations

import json
import os
import subprocess
import sys


def _run(seed: str) -> dict:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd()
    env["PYTHONHASHSEED"] = seed
    code = (
        "import json; "
        "from tests.v2.repair_v2_13_helpers import scene, patch_region; "
        "from learnflow_v2.repair import apply_safe_scenegraph_patches, compute_content_hash; "
        "r=apply_safe_scenegraph_patches(scene('s1'), (patch_region(),)); "
        "print(json.dumps({'scene_hash': r.repaired_scene_hash, 'probe_hash': compute_content_hash({'b':2,'a':1})}, sort_keys=True))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_cp2_13_fresh_process_and_hash_seed_replay_are_deterministic():
    assert _run("1") == _run("999")
