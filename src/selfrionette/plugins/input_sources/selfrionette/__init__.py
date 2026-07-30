"""Selfrionette device source with live and injected acquisition backends."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from enum import Enum

from selfrionette.plugins.input_sources.selfrionette.protocol import (
    LoadcellNormalizationConfig,
    LoadcellNormalizedInputIntentConverter,
    NormalizedLoadcellInputIntent,
    RawLoadcellVectorRecord,
    SerialDiagnosticEvent,
    SerialFrameParseError,
    SerialInputSource,
    normalize_loadcell_frame_for_mapping,
    parse_serial_frame_line,
)
from selfrionette.runtime.experiment.input_source import (
    InputSourceHealth,
    InputSourceHealthStatus,
    InputSourceRuntimeDependencies,
)
from selfrionette.schemas import RawInputFrame

_SERIAL_IMPORT_ERROR = (
    "serial module is required for live Selfrionette mode. "
    "Install pyserial or use injected lines."
)


class _LifecycleState(str, Enum):
    NEW = "new"
    STARTED = "started"
    START_FAILED = "start_failed"
    CLOSED = "closed"


class SelfrionetteInputSource:
    """1つのSelfrionette readerのexclusive lifecycle/health owner。

    constructionはI/Oを行わない。``start()`` だけがlive modeでserial portを開き、
    injected modeではcaller提供lineを読む。start failure後は``close()``までretryを拒否し、
    ``close()`` はportを閉じる。thread-safeではなく、同一runtime loopから直列利用する。
    """

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
        self._state = _LifecycleState.NEW

    def start(self) -> None:
        if self._state is _LifecycleState.STARTED:
            return
        if self._state is _LifecycleState.START_FAILED:
            raise RuntimeError(
                "Selfrionette input source must be closed after failed start before retry"
            )
        try:
            if self._injected_lines is not None:
                self._source = SerialInputSource.from_lines(self._injected_lines)
            else:
                if self._port is None:  # pragma: no cover - validated at construction
                    raise ValueError("port is required for live Selfrionette mode")
                try:
                    # pyserialはlive start時だけ必要なoptional hardware dependencyである。
                    import serial  # type: ignore[import-not-found]
                except ModuleNotFoundError as exc:
                    raise RuntimeError(_SERIAL_IMPORT_ERROR) from exc
                self._serial_port = serial.Serial(
                    port=self._port,
                    baudrate=self._baud_rate,
                )

                def lines() -> Iterator[str]:
                    while True:
                        raw_line = self._serial_port.readline()
                        if not raw_line:
                            continue
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if line:
                            yield line

                self._source = SerialInputSource(lines())
        except BaseException:
            self._state = _LifecycleState.START_FAILED
            raise
        self._state = _LifecycleState.STARTED

    def read_frame(self) -> RawInputFrame:
        if self._source is None:
            raise RuntimeError("Selfrionette input source is not started")
        return self._source.read_frame()

    def current_health(self) -> InputSourceHealth:
        if self._state is _LifecycleState.STARTED:
            return InputSourceHealth(InputSourceHealthStatus.ACTIVE, age_ms=0)
        reason = (
            "start_failed"
            if self._state is _LifecycleState.START_FAILED
            else "not_started"
        )
        return InputSourceHealth(
            InputSourceHealthStatus.DISCONNECTED,
            reason=reason,
            age_ms=0,
        )

    def close(self) -> None:
        serial_port = self._serial_port
        if serial_port is not None:
            serial_port.close()
        self._serial_port = None
        self._source = None
        self._state = _LifecycleState.CLOSED

    @property
    def diagnostics(self) -> tuple[SerialDiagnosticEvent, ...]:
        return () if self._source is None else self._source.diagnostics


def _validate_parameters(
    parameters: Mapping[str, object],
    *,
    runtime_dependencies: InputSourceRuntimeDependencies | None,
) -> tuple[str | None, int, tuple[str, ...] | None]:
    port = parameters.get("port")
    if port is not None and (
        not isinstance(port, str) or not port.strip()
    ):
        raise ValueError("port must be a non-empty string when provided")
    baud_rate = parameters.get("baud_rate", 115200)
    if type(baud_rate) is not int or baud_rate <= 0:
        raise ValueError("baud_rate must be positive")
    parameter_lines = parameters.get("lines")
    if parameter_lines is not None and not isinstance(parameter_lines, tuple):
        raise ValueError("Selfrionette injected lines must be a tuple")
    dependency_lines = (
        runtime_dependencies.line_source
        if runtime_dependencies is not None
        else None
    )
    selected_lines = dependency_lines if dependency_lines is not None else parameter_lines
    injected_lines = tuple(selected_lines) if selected_lines is not None else None
    if injected_lines is not None and any(
        not isinstance(line, str) for line in injected_lines
    ):
        raise ValueError("Selfrionette injected lines must contain strings")
    if port is not None and injected_lines is not None:
        raise ValueError("Selfrionette source cannot combine port and injected lines")
    if port is None and injected_lines is None:
        raise ValueError("port or injected lines are required for Selfrionette")
    return port, baud_rate, injected_lines


def build_reader(
    parameters: Mapping[str, object],
    *,
    runtime_dependencies: InputSourceRuntimeDependencies | None = None,
) -> SelfrionetteInputSource:
    """parameterを検証して未開始readerを返し、serial portは開かない。"""

    port, baud_rate, injected_lines = _validate_parameters(
        parameters,
        runtime_dependencies=runtime_dependencies,
    )
    return SelfrionetteInputSource(
        port=port,
        baud_rate=baud_rate,
        injected_lines=injected_lines,
    )


__all__ = [
    "LoadcellNormalizationConfig",
    "LoadcellNormalizedInputIntentConverter",
    "NormalizedLoadcellInputIntent",
    "RawLoadcellVectorRecord",
    "SelfrionetteInputSource",
    "SerialDiagnosticEvent",
    "SerialFrameParseError",
    "SerialInputSource",
    "build_reader",
    "normalize_loadcell_frame_for_mapping",
    "parse_serial_frame_line",
]
