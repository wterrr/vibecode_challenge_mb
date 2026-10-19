"""V3-56 reproducibility controls for OPTIONAL local-only ASR; never fetch or invoke model."""
import hashlib
import json
from types import SimpleNamespace
import pytest
from scripts.run_v3_56_local_asr_candidates import require_local_model, sha_file, run


def test_missing_local_weights_fails_before_asr_import(tmp_path):
    lic=tmp_path/"license.json"
    lic.write_text(json.dumps({"model_sha256":"0"*64,"model_source":"local",
        "license":"MIT","redistribution_cleared_or_local_use_permitted":True}))
    m=tmp_path/"nonexistent"
    with pytest.raises(FileNotFoundError):
        require_local_model(m,lic)


def test_license_hash_and_rights_must_match(tmp_path):
    model=tmp_path/"licensed_model"
    model.mkdir()
    (model/"model.bin").write_bytes(b"dummy-not-a-real-ASR-model")
    lic=tmp_path/"lic.json"
    payload={"model_sha256":"0"*64,"model_source":"test fixture","license":"MIT",
             "redistribution_cleared_or_local_use_permitted":True}
    lic.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError,match="ASR_MODEL_HASH_LICENSE_NOT_VERIFIED"):
        require_local_model(model,lic)
    payload["model_sha256"]=sha_file(model/"model.bin")
    payload["redistribution_cleared_or_local_use_permitted"]=False
    lic.write_text(json.dumps(payload))
    with pytest.raises(RuntimeError,match="ASR_MODEL_RIGHTS_NOT_CLEARED"):
        require_local_model(model,lic)


def test_original_input_media_sha_required_before_any_asr(tmp_path):
    wrong=tmp_path/"wrong.mp4"
    wrong.write_bytes(b"not-the-uploaded-video")
    with pytest.raises(RuntimeError,match="ORIGINAL_VIDEO_SHA_MISMATCH"):
        run(SimpleNamespace(video=str(wrong),model_dir="/not-present",
            model_license="/not-present",output=str(tmp_path/"out.json"),
            allow_private_local_repo=False))
