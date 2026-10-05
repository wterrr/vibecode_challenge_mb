from __future__ import annotations

import json
import os
import subprocess
import sys


def test_cp2_12_builds_request_in_fresh_interpreter():
    env = dict(os.environ)
    env["PYTHONPATH"] = os.getcwd()
    code = (
        "from tests.v2.critic_v2_12_helpers import good_request; "
        "r=good_request(); "
        "assert r.scene_id == 'scene_critic'; "
        "assert len(r.frames) >= 2; "
        "print(r.to_canonical_json())"
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
    payload = json.loads(proc.stdout)
    assert payload["scene_id"] == "scene_critic"
