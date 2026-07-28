"""Deterministic production Input Source Plugin catalog."""

from __future__ import annotations

from collections.abc import Iterable

from selfrionette.plugins.input_source_registration import InputSourcePluginRegistration
from selfrionette.runtime.experiment.contracts import PluginSelection
from selfrionette.runtime.experiment.input_source import InputSourcePlugin
from selfrionette.runtime.experiment.registry import VersionedPluginRegistry


class InputSourceCatalog:
    def __init__(self, registrations: Iterable[InputSourcePluginRegistration]) -> None:
        self._registrations = tuple(
            sorted(registrations, key=lambda item: item.catalog_order)
        )
        self._by_alias: dict[str, InputSourcePluginRegistration] = {}
        generic_cli_orders: set[int] = set()
        catalog_orders: set[int] = set()
        for registration in self._registrations:
            for alias in registration.cli_aliases:
                if alias in self._by_alias:
                    raise ValueError(f"duplicate input source CLI alias: {alias!r}")
                self._by_alias[alias] = registration
            if registration.catalog_order in catalog_orders:
                raise ValueError(
                    "duplicate input source catalog order: "
                    f"{registration.catalog_order!r}"
                )
            catalog_orders.add(registration.catalog_order)
            if registration.generic_cli_exposed:
                order = registration.generic_cli_order
                if order in generic_cli_orders:
                    raise ValueError(f"duplicate generic input source CLI order: {order!r}")
                generic_cli_orders.add(order)
        self._by_alias = dict(sorted(self._by_alias.items()))
        self._registry = VersionedPluginRegistry(
            (registration.plugin for registration in self._registrations),
            kind="input source plugin",
        )

    @property
    def ids(self) -> tuple[str, ...]:
        return self._registry.ids

    @property
    def aliases(self) -> tuple[str, ...]:
        return tuple(
            registration.cli_aliases[0]
            for registration in sorted(
                (
                    item
                    for item in self._registrations
                    if item.generic_cli_exposed
                ),
                key=lambda item: item.generic_cli_order,
            )
        )

    @property
    def registrations(self) -> tuple[InputSourcePluginRegistration, ...]:
        return self._registrations

    @property
    def registry(self) -> VersionedPluginRegistry[InputSourcePlugin]:
        return self._registry

    def resolve(self, alias: str) -> InputSourcePluginRegistration:
        try:
            return self._by_alias[alias]
        except KeyError as exc:
            raise ValueError(f"unsupported input source: {alias!r}") from exc

    def resolve_plugin(self, selection: PluginSelection) -> InputSourcePlugin:
        return self._registry.resolve(selection)

    def resolve_selection(self, alias: str) -> PluginSelection:
        registration = self.resolve(alias)
        return PluginSelection(
            registration.plugin.identity.name,
            registration.plugin.identity.version,
        )


from selfrionette.plugins.input_source_discovery import (
    InputSourcePluginDiscoveryError,
    discover_production_input_source_plugins,
)


try:
    INPUT_SOURCE_CATALOG = InputSourceCatalog(
        discover_production_input_source_plugins()
    )
except ValueError as exc:
    raise InputSourcePluginDiscoveryError(str(exc)) from exc
INPUT_SOURCE_PLUGIN_REGISTRY = INPUT_SOURCE_CATALOG.registry
SUPPORTED_INPUT_SOURCE_NAMES = INPUT_SOURCE_CATALOG.aliases


def get_input_source_registration(alias: str) -> InputSourcePluginRegistration:
    return INPUT_SOURCE_CATALOG.resolve(alias)


def resolve_input_source_plugin(selection: PluginSelection) -> InputSourcePlugin:
    return INPUT_SOURCE_CATALOG.resolve_plugin(selection)


__all__ = [
    "INPUT_SOURCE_CATALOG",
    "INPUT_SOURCE_PLUGIN_REGISTRY",
    "InputSourceCatalog",
    "SUPPORTED_INPUT_SOURCE_NAMES",
    "get_input_source_registration",
    "resolve_input_source_plugin",
]
