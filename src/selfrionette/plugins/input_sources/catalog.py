"""Deterministic production Input Source Plugin catalog."""

from __future__ import annotations

from types import MappingProxyType

from selfrionette.plugins.input_sources.registration import INPUT_SOURCE_REGISTRATIONS, InputSourcePluginRegistration
from selfrionette.runtime.experiment.contracts import PluginSelection
from selfrionette.runtime.experiment.input_source import InputSourcePlugin
from selfrionette.runtime.experiment.registry import VersionedPluginRegistry


class InputSourceCatalog:
    def __init__(self, registrations: tuple[InputSourcePluginRegistration, ...]) -> None:
        self._registrations = tuple(registrations)
        self._by_alias: dict[str, InputSourcePluginRegistration] = {}
        for registration in self._registrations:
            for alias in registration.cli_aliases:
                if alias in self._by_alias:
                    raise ValueError(f"duplicate input source CLI alias: {alias!r}")
                self._by_alias[alias] = registration
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
            for registration in self._registrations
            if registration.generic_cli_exposed
        )

    @property
    def registrations(self) -> tuple[InputSourcePluginRegistration, ...]:
        return self._registrations

    def resolve(self, alias: str) -> InputSourcePluginRegistration:
        try:
            return self._by_alias[alias]
        except KeyError as exc:
            raise ValueError(f"unsupported input source: {alias!r}") from exc

    def resolve_plugin(self, selection: PluginSelection) -> InputSourcePlugin:
        return self._registry.resolve(selection)

    def resolve_selection(self, alias: str) -> PluginSelection:
        registration = self.resolve(alias)
        return PluginSelection(registration.plugin.identity.name, registration.plugin.identity.version)


INPUT_SOURCE_CATALOG = InputSourceCatalog(INPUT_SOURCE_REGISTRATIONS)
INPUT_SOURCE_PLUGIN_REGISTRY = VersionedPluginRegistry(
    (registration.plugin for registration in INPUT_SOURCE_REGISTRATIONS),
    kind="input source plugin",
)
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
