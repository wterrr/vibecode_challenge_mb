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
        "from tests.v2.video_critic_v2_14_helpers import make_request; "
        "from learnflow_v2.videoqa import compute_video_critic_request_hash; "
        "r=make_request(); print(json.dumps({'hash': compute_video_critic_request_hash(r), 'json': r.to_canonical_json()}, sort_keys=True))"
    )
    proc = subprocess.run([sys.executable, "-c", code], cwd=os.getcwd(), env=env, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_video_critic_fresh_process_and_hash_seed_replay_are_deterministic():
    assert _run("1") == _run("999")
