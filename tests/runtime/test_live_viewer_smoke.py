from __future__ import annotations

from selfrionette.runtime.live_viewer_smoke import (
    build_live_viewer_smoke_parser,
    build_live_viewer_smoke_viewer_url,
)


def test_live_viewer_smoke_parser_defaults_match_manual_smoke_docs() -> None:
    args = build_live_viewer_smoke_parser().parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 8766
    assert args.steps == 3
    assert args.grace_period_s == 5.0


def test_live_viewer_smoke_viewer_url_helper_uses_loopback_endpoint() -> None:
    assert build_live_viewer_smoke_viewer_url("127.0.0.1", 8766) == "ws://127.0.0.1:8766"
