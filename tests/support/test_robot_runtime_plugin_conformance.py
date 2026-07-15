from __future__ import annotations

from dataclasses import replace
from math import inf, nan

import pytest

from tests.robots.fast_arm_conformance_case import (
    FAST_ARM_ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASE,
)
from tests.robots.robot_runtime_plugin_conformance_cases import (
    ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASES,
)
from tests.support.robot_runtime_plugin_conformance import (
    validate_conformance_case_registry,
)


BASE_CASE = FAST_ARM_ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASE


def _replace_nested_case(
    collection_name: str,
    **changes: object,
):
    nested_cases = getattr(BASE_CASE, collection_name)
    updated_first = replace(nested_cases[0], **changes)
    return replace(
        BASE_CASE,
        **{collection_name: (updated_first, *nested_cases[1:])},
    )


def _replace_duplicate_nested_case(collection_name: str):
    nested_cases = getattr(BASE_CASE, collection_name)
    duplicate = replace(nested_cases[1], case_id=nested_cases[0].case_id)
    return replace(
        BASE_CASE,
        **{collection_name: (nested_cases[0], duplicate, *nested_cases[2:])},
    )


def test_current_registry_is_valid() -> None:
    validate_conformance_case_registry(ROBOT_RUNTIME_PLUGIN_CONFORMANCE_CASES)


def test_empty_registry_fails_fast() -> None:
    with pytest.raises(AssertionError, match="registry must not be empty"):
        validate_conformance_case_registry(())


def test_duplicate_robot_case_id_fails_fast() -> None:
    duplicate = replace(BASE_CASE, case_id=BASE_CASE.case_id)
    with pytest.raises(AssertionError, match="duplicate conformance case IDs"):
        validate_conformance_case_registry((BASE_CASE, duplicate))


def test_duplicate_profile_id_fails_fast() -> None:
    duplicate = replace(BASE_CASE, case_id="duplicate-profile-case")
    with pytest.raises(AssertionError, match="duplicate conformance profile IDs"):
        validate_conformance_case_registry((BASE_CASE, duplicate))


@pytest.mark.parametrize(
    ("field_name", "value"),
    (
        ("expected_qpos_dimension", 0),
        ("expected_qpos_dimension", -1),
        ("expected_qvel_dimension", 0),
        ("expected_qvel_dimension", -1),
        ("expected_qpos_dimension", True),
        ("expected_qvel_dimension", False),
    ),
)
def test_robot_dimensions_must_be_positive_integers(
    field_name: str,
    value: object,
) -> None:
    invalid = replace(BASE_CASE, **{field_name: value})
    with pytest.raises(
        AssertionError,
        match=rf"{field_name} must be a positive integer",
    ):
        validate_conformance_case_registry((invalid,))


@pytest.mark.parametrize(
    "collection_name",
    (
        "known_fk_cases",
        "ik_round_trip_cases",
        "mujoco_endpoint_cases",
        "fail_closed_cases",
    ),
)
def test_nested_case_ids_must_be_unique_per_collection(collection_name: str) -> None:
    invalid = _replace_duplicate_nested_case(collection_name)
    with pytest.raises(
        AssertionError,
        match=rf"{collection_name}.*duplicate case ID",
    ):
        validate_conformance_case_registry((invalid,))


@pytest.mark.parametrize(
    "collection_name",
    (
        "known_fk_cases",
        "ik_round_trip_cases",
        "mujoco_endpoint_cases",
        "fail_closed_cases",
    ),
)
def test_nested_case_ids_must_be_non_empty(collection_name: str) -> None:
    invalid = _replace_nested_case(collection_name, case_id="")
    with pytest.raises(
        AssertionError,
        match=rf"{collection_name}.*empty case ID",
    ):
        validate_conformance_case_registry((invalid,))


def test_known_fk_qpos_must_be_finite() -> None:
    invalid = _replace_nested_case(
        "known_fk_cases",
        qpos=(nan, *BASE_CASE.known_fk_cases[0].qpos[1:]),
    )
    with pytest.raises(AssertionError, match="known_fk_cases.*qpos.*finite"):
        validate_conformance_case_registry((invalid,))


def test_ik_seed_qpos_must_be_finite() -> None:
    invalid = _replace_nested_case(
        "ik_round_trip_cases",
        seed_qpos=(inf, *BASE_CASE.ik_round_trip_cases[0].seed_qpos[1:]),
    )
    with pytest.raises(AssertionError, match="ik_round_trip_cases.*seed_qpos.*finite"):
        validate_conformance_case_registry((invalid,))


def test_mujoco_case_qpos_must_be_finite() -> None:
    invalid = _replace_nested_case(
        "mujoco_endpoint_cases",
        qpos=(-inf, *BASE_CASE.mujoco_endpoint_cases[0].qpos[1:]),
    )
    with pytest.raises(AssertionError, match="mujoco_endpoint_cases.*qpos.*finite"):
        validate_conformance_case_registry((invalid,))


@pytest.mark.parametrize("invalid_value", (True, "not-a-number"))
def test_known_fk_qpos_rejects_non_numeric_values(invalid_value: object) -> None:
    invalid = _replace_nested_case(
        "known_fk_cases",
        qpos=(invalid_value, *BASE_CASE.known_fk_cases[0].qpos[1:]),
    )
    with pytest.raises(AssertionError, match="known_fk_cases.*qpos.*numeric"):
        validate_conformance_case_registry((invalid,))


@pytest.mark.parametrize(
    ("changes", "error_pattern"),
    (
        ({"description": ""}, "description must be non-empty"),
        ({"run": None}, "run must be callable"),
        ({"exception_type": object}, "exception_type must be an Exception class"),
        ({"message_pattern": ""}, "message_pattern must be non-empty"),
    ),
)
def test_fail_closed_declarations_are_validated(
    changes: dict[str, object],
    error_pattern: str,
) -> None:
    invalid = _replace_nested_case("fail_closed_cases", **changes)
    with pytest.raises(AssertionError, match=error_pattern):
        validate_conformance_case_registry((invalid,))
