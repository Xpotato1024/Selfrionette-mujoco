"""動画出力の入出力境界。既存動画と元trialを破壊しない。"""
import argparse
import importlib.util
from pathlib import Path
import pytest

script=Path(__file__).resolve().parents[2]/"scripts/viewer/export_trial_video.py"
spec=importlib.util.spec_from_file_location("video_export_test",script)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def options(tmp_path, **values):
    result=argparse.Namespace(trial=tmp_path/"trial",output=tmp_path/"clip.mp4",width=1920,height=1080,
        fps=30,camera="operator",browser=None)
    for name,value in values.items():setattr(result,name,value)
    return result


def test_existing_file_not_overwritten(tmp_path):
    args=options(tmp_path)
    args.output.write_bytes(b"previous video")
    with pytest.raises(ValueError,match="never overwritten"):
        module.export(args)
    assert args.output.read_bytes()==b"previous video"


def test_existing_sidecar_not_overwritten(tmp_path):
    args=options(tmp_path)
    args.output.with_suffix(".json").write_bytes(b"previous evidence")
    with pytest.raises(ValueError,match="never overwritten"):
        module.export(args)


def test_cannot_write_inside_trial(tmp_path):
    with pytest.raises(ValueError,match="immutable trial"):
        module.export(options(tmp_path,output=tmp_path/"trial/clip.mp4"))


@pytest.mark.parametrize("changes",[{"fps":0},{"fps":True},{"fps":121},{"width":101},{"height":9999}])
def test_invalid_export_options_fail_before_process_start(tmp_path,changes):
    with pytest.raises(ValueError):module.export(options(tmp_path,**changes))


def test_explicit_browser_required_to_exist(tmp_path):
    with pytest.raises(FileNotFoundError):module.browser_path(tmp_path/"absent.exe")
