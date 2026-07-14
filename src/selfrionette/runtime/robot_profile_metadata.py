"""Authoritative robot compatibility metadata merge boundary."""

from __future__ import annotations

from collections.abc import Mapping

ROBOT_PROFILE_METADATA_KEYS = frozenset(
    {
        "robot_profile_id",
        "model_contract_version",
        "robot_joint_names",
        "robot_qpos_dimension",
    }
)


def merge_runtime_metadata(
    *metadata_sources: Mapping[str, object] | None,
    authoritative_profile_metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Merge ordinary metadata, then overwrite reserved keys authoritatively.

    Production composition supplies all four reserved keys. Generic pipelines
    pass no authoritative metadata and retain their previous merge behavior.
    """

    merged: dict[str, object] = {}
    for source in metadata_sources:
        if source is not None:
            merged.update(source)

    if authoritative_profile_metadata is None:
        return merged

    actual_keys = frozenset(authoritative_profile_metadata)
    if actual_keys != ROBOT_PROFILE_METADATA_KEYS:
        missing = tuple(sorted(ROBOT_PROFILE_METADATA_KEYS - actual_keys))
        unexpected = tuple(sorted(actual_keys - ROBOT_PROFILE_METADATA_KEYS))
        raise ValueError(
            "authoritative robot profile metadata keys mismatch: "
            f"missing={missing}, unexpected={unexpected}"
        )
    merged.update(authoritative_profile_metadata)
    return merged


__all__ = ["ROBOT_PROFILE_METADATA_KEYS", "merge_runtime_metadata"]
