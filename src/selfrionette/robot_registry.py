"""Controlled deterministic registries for known robot declarations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import Generic, Protocol, TypeVar

from selfrionette.robot_profile import RobotProfile


class _Identified(Protocol):
    @property
    def profile_id(self) -> str: ...


T = TypeVar("T", bound=_Identified)


class ImmutableRegistry(Generic[T]):
    def __init__(self, entries: Iterable[T], *, kind: str) -> None:
        values: dict[str, T] = {}
        for entry in entries:
            if entry.profile_id in values:
                raise ValueError(f"duplicate {kind} registration: {entry.profile_id!r}")
            values[entry.profile_id] = entry
        self._kind = kind
        self._values: Mapping[str, T] = MappingProxyType(values)

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(self._values)

    def resolve(self, profile_id: str) -> T:
        try:
            return self._values[profile_id]
        except KeyError as exc:
            raise ValueError(
                f"unknown {self._kind} ID {profile_id!r}; available: {self.ids}"
            ) from exc


def _build_robot_profile_registry() -> ImmutableRegistry[RobotProfile]:
    from selfrionette.robots.fast_arm import FAST_ARM_ROBOT_PROFILE

    return ImmutableRegistry((FAST_ARM_ROBOT_PROFILE,), kind="robot profile")


ROBOT_PROFILE_REGISTRY = _build_robot_profile_registry()


def resolve_robot_profile(profile_id: str) -> RobotProfile:
    return ROBOT_PROFILE_REGISTRY.resolve(profile_id)


def registered_robot_profile_ids() -> tuple[str, ...]:
    return ROBOT_PROFILE_REGISTRY.ids


__all__ = [
    "ImmutableRegistry",
    "registered_robot_profile_ids",
    "resolve_robot_profile",
]
