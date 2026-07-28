"""Loadcell serial source adapter; endpoint mapping is owned by plugins.mappings."""

from collections.abc import Iterator, Mapping

from selfrionette.plugins.input_sources._loadcell import (
    SerialInputSource,
    normalize_loadcell_frame_for_mapping,
)
from selfrionette.plugins.input_sources._common import ManagedFrameHealthReader
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceRuntimeDependencies,
)

_SERIAL_IMPORT_ERROR = (
    "serial module is required for live serial mode. Install pyserial or run fixture mode."
)
_NOT_STARTED_HEALTH = InputSourceHealth(
    InputSourceHealthStatus.DISCONNECTED,
    reason="not_started",
    age_ms=0,
)
_STARTED_HEALTH = InputSourceHealth(
    InputSourceHealthStatus.ACTIVE,
    age_ms=0,
)
_START_FAILURE_HEALTH = InputSourceHealth(
    InputSourceHealthStatus.DISCONNECTED,
    reason="start_failed",
    age_ms=0,
)


class _ManagedSerialDelegate:
    def __init__(
        self,
        *,
        port: str | None,
        baud_rate: int,
        injected_lines: tuple[str, ...] | None,
    ) -> None:
        self._port = port
        self._baud_rate = baud_rate
        self._injected_lines = injected_lines
        self._serial_port = None
        self._source: SerialInputSource | None = None

    def start(self) -> None:
        if self._source is not None:
            return
        if self._injected_lines is not None:
            self._source = SerialInputSource.from_lines(self._injected_lines)
            return
        if self._port is None:  # pragma: no cover - validated before construction
            raise ValueError("port is required for live serial mode")
        try:
            import serial  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:
            raise RuntimeError(_SERIAL_IMPORT_ERROR) from exc
        self._serial_port = serial.Serial(port=self._port, baudrate=self._baud_rate)

        def lines() -> Iterator[str]:
            while True:
                raw_line = self._serial_port.readline()
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace").strip()
                if line:
                    yield line

        self._source = SerialInputSource(lines())

    def read_frame(self):
        if self._source is None:
            raise RuntimeError("loadcell serial input source is not started")
        return self._source.read_frame()

    def close(self) -> None:
        serial_port = self._serial_port
        if serial_port is not None:
            serial_port.close()
        self._serial_port = None
        self._source = None


def _validate_parameters(
    parameters: Mapping[str, object],
    *,
    runtime_dependencies: InputSourceRuntimeDependencies | None,
) -> tuple[str | None, int, tuple[str, ...] | None]:
    port = parameters.get("port")
    if port is not None:
        if not isinstance(port, str):
            raise ValueError("port must be a string when provided")
        if not port.strip():
            raise ValueError("port must not be empty")

    baud_rate = parameters.get("baud_rate", 115200)
    if type(baud_rate) is not int or baud_rate <= 0:
        raise ValueError("baud_rate must be positive")

    parameter_lines = parameters.get("lines")
    if parameter_lines is not None and not isinstance(parameter_lines, tuple):
        raise ValueError("loadcell serial injected lines must be a tuple")
    dependency_lines = (
        runtime_dependencies.line_source
        if runtime_dependencies is not None
        else None
    )
    selected_lines = dependency_lines if dependency_lines is not None else parameter_lines
    injected_lines = tuple(selected_lines) if selected_lines is not None else None
    if injected_lines is not None and any(not isinstance(line, str) for line in injected_lines):
        raise ValueError("loadcell serial injected lines must contain strings")

    if port is not None and injected_lines is not None:
        raise ValueError(
            "loadcell serial input source cannot combine port and injected lines"
        )
    if port is None and injected_lines is None:
        raise ValueError("port is required for live serial mode")

    return port, baud_rate, injected_lines


def build_reader(
    parameters: Mapping[str, object],
    *,
    runtime_dependencies: InputSourceRuntimeDependencies | None = None,
) -> ManagedFrameHealthReader:
    port, baud_rate, injected_lines = _validate_parameters(
        parameters,
        runtime_dependencies=runtime_dependencies,
    )
    delegate = _ManagedSerialDelegate(
        port=port,
        baud_rate=baud_rate,
        injected_lines=injected_lines,
    )
    return ManagedFrameHealthReader(
        delegate,
        _NOT_STARTED_HEALTH,
        started_health=_STARTED_HEALTH,
        start_failure_health=_START_FAILURE_HEALTH,
        closed_health=_NOT_STARTED_HEALTH,
    )


__all__ = ["build_reader"]
