from __future__ import annotations

from dataclasses import dataclass

from selfrionette.mujoco_backend.model_contract import (
    ResolvedModelReference,
    fast_arm_model_name_contract,
    resolve_fast_arm_end_effector_reference,
    resolve_fast_arm_tip_reference,
)
from selfrionette.schemas import BodyTransform, MuJoCoState, SiteTransform
from selfrionette.schemas.types import Vector3

_FAST_ARM_CONTRACT = fast_arm_model_name_contract()
_ENDPOINT_UNIT = _FAST_ARM_CONTRACT.position_unit
_ENDPOINT_COORDINATE_FRAME = _FAST_ARM_CONTRACT.coordinate_frame


def _import_mujoco() -> object:
    import mujoco

    return mujoco


def _vector3(values: object) -> Vector3:
    x, y, z = values  # type: ignore[misc]
    return (float(x), float(y), float(z))


def _missing_name_message(*, kind: str, name: str, role: str) -> str:
    return f"missing {kind} name {name!r} for expected role '{role}'"


@dataclass(frozen=True, slots=True)
class RuntimeMuJoCoSiteEndpointEvaluation:
    role: str
    kind: str
    name: str
    position_m: Vector3
    unit: str = _ENDPOINT_UNIT
    coordinate_frame: str = _ENDPOINT_COORDINATE_FRAME


def _resolve_reference_position_from_model_data(
    model: object,
    data: object,
    reference: ResolvedModelReference,
) -> Vector3:
    mujoco = _import_mujoco()
    mujoco.mj_forward(model, data)

    if reference.kind == "site":
        object_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, reference.name)
        if object_id < 0:
            raise ValueError(
                _missing_name_message(
                    kind="site",
                    name=reference.name,
                    role=reference.role,
                )
            )
        return _vector3(data.site_xpos[object_id])

    if reference.kind == "body":
        object_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, reference.name)
        if object_id < 0:
            raise ValueError(
                _missing_name_message(
                    kind="body",
                    name=reference.name,
                    role=reference.role,
                )
            )
        return _vector3(data.xpos[object_id])

    raise ValueError(f"unsupported MuJoCo endpoint reference kind: {reference.kind!r}")


def _resolve_reference_position_from_state(
    state: MuJoCoState,
    reference: ResolvedModelReference,
) -> Vector3:
    transforms: tuple[SiteTransform | BodyTransform, ...]
    if reference.kind == "site":
        transforms = state.sites
    elif reference.kind == "body":
        transforms = state.bodies
    else:
        raise ValueError(f"unsupported MuJoCo endpoint reference kind: {reference.kind!r}")

    for transform in transforms:
        if transform.name == reference.name:
            return transform.position_m

    raise ValueError(
        _missing_name_message(
            kind=reference.kind,
            name=reference.name,
            role=reference.role,
        )
    )


def _resolve_body_position_from_state(
    state: MuJoCoState,
    *,
    body_name: str,
    role: str,
) -> Vector3:
    for body in state.bodies:
        if body.name == body_name:
            return body.position_m

    raise ValueError(
        _missing_name_message(
            kind="body",
            name=body_name,
            role=role,
        )
    )


def _resolve_fast_arm_reference_from_state(
    state: MuJoCoState,
    *,
    role: str,
    allow_body_fallback: bool = False,
) -> ResolvedModelReference:
    if any(site.name == _FAST_ARM_CONTRACT.tip_site_name for site in state.sites):
        return ResolvedModelReference(
            role=role,
            kind="site",
            name=_FAST_ARM_CONTRACT.tip_site_name,
        )

    if allow_body_fallback:
        if any(body.name == _FAST_ARM_CONTRACT.tip_body_name for body in state.bodies):
            return ResolvedModelReference(
                role=role,
                kind="body",
                name=_FAST_ARM_CONTRACT.tip_body_name,
            )

        raise ValueError(
            _missing_name_message(
                kind="body",
                name=_FAST_ARM_CONTRACT.tip_body_name,
                role=f"{role} fallback",
            )
        )

    raise ValueError(
        _missing_name_message(
            kind="site",
            name=_FAST_ARM_CONTRACT.tip_site_name,
            role=role,
        )
    )


def _build_endpoint_evaluation(
    *,
    reference: ResolvedModelReference,
    position_m: Vector3,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    return RuntimeMuJoCoSiteEndpointEvaluation(
        role=reference.role,
        kind=reference.kind,
        name=reference.name,
        position_m=position_m,
    )


def extract_fast_arm_tip_site_endpoint(
    model: object,
    data: object,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    reference = resolve_fast_arm_tip_reference(model, allow_body_fallback=allow_body_fallback)
    return _build_endpoint_evaluation(
        reference=reference,
        position_m=_resolve_reference_position_from_model_data(model, data, reference),
    )


def extract_fast_arm_end_effector_site_endpoint(
    model: object,
    data: object,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    reference = resolve_fast_arm_end_effector_reference(model, allow_body_fallback=allow_body_fallback)
    return _build_endpoint_evaluation(
        reference=reference,
        position_m=_resolve_reference_position_from_model_data(model, data, reference),
    )


def extract_mujoco_site_endpoint(
    model: object,
    data: object,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    return extract_fast_arm_tip_site_endpoint(model, data, allow_body_fallback=allow_body_fallback)


def extract_fast_arm_tip_site_endpoint_from_state(
    state: MuJoCoState,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    reference = _resolve_fast_arm_reference_from_state(
        state,
        role="tip",
        allow_body_fallback=allow_body_fallback,
    )
    return _build_endpoint_evaluation(
        reference=reference,
        position_m=_resolve_reference_position_from_state(state, reference),
    )


def extract_fast_arm_end_effector_site_endpoint_from_state(
    state: MuJoCoState,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    reference = _resolve_fast_arm_reference_from_state(
        state,
        role="end_effector",
        allow_body_fallback=allow_body_fallback,
    )
    return _build_endpoint_evaluation(
        reference=reference,
        position_m=_resolve_reference_position_from_state(state, reference),
    )


def extract_fast_arm_base_link_position_from_state(state: MuJoCoState) -> Vector3:
    return _resolve_body_position_from_state(
        state,
        body_name="base_link",
        role="solver base",
    )


def extract_mujoco_site_endpoint_from_state(
    state: MuJoCoState,
    *,
    allow_body_fallback: bool = False,
) -> RuntimeMuJoCoSiteEndpointEvaluation:
    return extract_fast_arm_tip_site_endpoint_from_state(
        state,
        allow_body_fallback=allow_body_fallback,
    )


__all__ = [
    "RuntimeMuJoCoSiteEndpointEvaluation",
    "extract_fast_arm_end_effector_site_endpoint",
    "extract_fast_arm_end_effector_site_endpoint_from_state",
    "extract_fast_arm_base_link_position_from_state",
    "extract_fast_arm_tip_site_endpoint",
    "extract_fast_arm_tip_site_endpoint_from_state",
    "extract_mujoco_site_endpoint",
    "extract_mujoco_site_endpoint_from_state",
]
