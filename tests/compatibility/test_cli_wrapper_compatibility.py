"""Explicit compatibility wrapper parity evidence retained until C4."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

from selfrionette.cli.main import build_parser


ROOT = Path(__file__).resolve().parents[2]


def _load_script(relative_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DRY_RUN_WRAPPER = _load_script(
    "scripts/compatibility/run_replay_mujoco_dry_run.py",
    "compatibility_dry_run",
)
VIEWER_WRAPPER = _load_script(
    "scripts/compatibility/run_replay_mujoco_websocket_publisher.py",
    "compatibility_viewer",
)


def _option_actions(parser: argparse.ArgumentParser) -> dict[str, argparse.Action]:
    return {
        option: action
        for action in parser._actions
        for option in action.option_strings
        if option not in {"-h", "--help"}
    }


def _canonical_subparser(command: str) -> argparse.ArgumentParser:
    subparsers = build_parser()._subparsers
    assert subparsers is not None
    return subparsers._group_actions[0].choices[command]


def test_wrapper_options_and_defaults_match_canonical_cli_except_required_robot() -> None:
    pairs = (
        (DRY_RUN_WRAPPER.build_parser(), _canonical_subparser("replay")),
        (VIEWER_WRAPPER.build_parser(), _canonical_subparser("viewer")),
    )
    for wrapper_parser, canonical_parser in pairs:
        wrapper_actions = _option_actions(wrapper_parser)
        canonical_actions = _option_actions(canonical_parser)
        canonical_actions.pop("--robot")
        assert wrapper_actions.keys() == canonical_actions.keys()
        assert {
            option: action.default
            for option, action in wrapper_actions.items()
        } == {
            option: action.default
            for option, action in canonical_actions.items()
        }


def test_wrapper_validation_wording_gap_is_explicitly_deferred() -> None:
    wrapper_steps = _option_actions(DRY_RUN_WRAPPER.build_parser())["--steps"]
    canonical_steps = _option_actions(_canonical_subparser("replay"))["--steps"]
    assert wrapper_steps.type is not None
    assert canonical_steps.type is not None

    try:
        wrapper_steps.type("0")
    except argparse.ArgumentTypeError as exc:
        wrapper_message = str(exc)
    try:
        canonical_steps.type("0")
    except argparse.ArgumentTypeError as exc:
        canonical_message = str(exc)

    assert wrapper_message == "steps must be a positive integer"
    assert canonical_message == "value must be a positive integer"
    assert wrapper_message != canonical_message
