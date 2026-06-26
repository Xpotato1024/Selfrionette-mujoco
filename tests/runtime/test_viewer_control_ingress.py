from __future__ import annotations

import pytest

from selfrionette.runtime import build_viewer_input_source, ingest_viewer_control_message
from selfrionette.schemas import ViewerControlMessageError


def test_viewer_control_ingress_validates_json_before_source_update() -> None:
    source = build_viewer_input_source()

    with pytest.raises(ViewerControlMessageError, match="malformed JSON"):
        ingest_viewer_control_message(source, "{not json")

    assert source.last_control_message is None
    assert source.read_frame().metadata["source_active"] is False
