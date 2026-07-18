from __future__ import annotations

import importlib
import sys

import pytest

cli = importlib.import_module("selfrionette.cli.main")


class _BundleWithCapabilities:
    def provider(self, identity):
        return object()


class _BundleWithoutCapabilities:
    def provider(self, identity):
        raise ValueError(
            f"unsupported Robot Bundle capability {identity.canonical_id!r}; provided=()"
        )


def test_help_is_deterministic(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--help"])

    assert exc_info.value.code == 0
    assert "{replay,viewer}" in capsys.readouterr().out


def test_invalid_argument_uses_argparse_exit_status(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["replay", "--robot", "fast_arm", "--steps", "0"])

    assert exc_info.value.code == 2
    assert "value must be a positive integer" in capsys.readouterr().err


def test_unknown_robot_returns_one_without_loading_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic_module = "selfrionette.plugins.robots.fast_arm.diagnostics"
    sys.modules.pop(diagnostic_module, None)

    def reject_unknown(robot_id: str):
        raise ValueError(f"unknown Robot Plugin ID {robot_id!r}; available: ('fast_arm',)")

    monkeypatch.setattr(cli, "resolve_robot_bundle", reject_unknown)

    assert cli.main(["replay", "--robot", "unknown"]) == 1
    assert "unknown Robot Plugin ID 'unknown'" in capsys.readouterr().err
    assert diagnostic_module not in sys.modules


def test_missing_capability_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "resolve_robot_bundle", lambda robot_id: _BundleWithoutCapabilities())

    assert cli.main(["replay", "--robot", "limited"]) == 1
    assert "unsupported Robot Bundle capability" in capsys.readouterr().err


def test_replay_resolves_bundle_and_forwards_robot_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved: list[str] = []
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        cli,
        "resolve_robot_bundle",
        lambda robot_id: (resolved.append(robot_id), _BundleWithCapabilities())[1],
    )
    monkeypatch.setattr(cli, "run_replay_mujoco_dry_run", lambda **kwargs: calls.append(kwargs))

    assert cli.main(["replay", "--robot", "selected", "--steps", "2"]) == 0
    assert resolved == ["selected"]
    assert calls[0]["robot_profile_id"] == "selected"
    assert calls[0]["steps"] == 2


def test_viewer_resolves_bundle_and_forwards_robot_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(cli, "resolve_robot_bundle", lambda robot_id: _BundleWithCapabilities())
    monkeypatch.setattr(
        cli,
        "run_replay_mujoco_websocket_publisher",
        lambda **kwargs: calls.append(kwargs),
    )

    assert cli.main(["viewer", "--robot", "selected", "--port", "9000"]) == 0
    assert calls[0]["robot_profile_id"] == "selected"
    assert calls[0]["port"] == 9000


def test_runtime_failure_returns_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "resolve_robot_bundle", lambda robot_id: _BundleWithCapabilities())

    def fail(**kwargs):
        raise RuntimeError("runtime failed")

    monkeypatch.setattr(cli, "run_replay_mujoco_dry_run", fail)

    assert cli.main(["replay", "--robot", "selected"]) == 1
    assert capsys.readouterr().err == "selfrionette: error: runtime failed\n"
