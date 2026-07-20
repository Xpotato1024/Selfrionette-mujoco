"""Loadcell serial source adapter; mapping remains outside this package."""

from collections.abc import Iterable, Iterator, Mapping

from selfrionette.input_sources.loadcell_serial import SerialInputSource
from selfrionette.plugins.input_sources._common import ManagedFrameHealthReader
from selfrionette.runtime.experiment.input_source import InputSourceHealth, InputSourceHealthStatus, InputSourceRuntimeDependencies

_SERIAL_IMPORT_ERROR = "serial module is required for live serial mode. Install pyserial or run fixture mode."


class _ManagedSerialDelegate:
    def __init__(self, *, port: str | None, baud_rate: int, injected_lines: Iterable[str] | None) -> None:
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
        if self._port is None:
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
        assert self._source is not None
        return self._source.read_frame()

    def close(self) -> None:
        if self._serial_port is not None:
            self._serial_port.close()
            self._serial_port = None


def build_reader(parameters: Mapping[str, object], *, runtime_dependencies: InputSourceRuntimeDependencies | None = None) -> ManagedFrameHealthReader:
    lines = runtime_dependencies.line_source if runtime_dependencies is not None and runtime_dependencies.line_source is not None else parameters.get("lines")
    port = parameters.get("port")
    if port is not None and not isinstance(port, str):
        raise ValueError("port must be a string when provided")
    baud_rate = parameters.get("baud_rate", 115200)
    delegate = _ManagedSerialDelegate(
        port=port,
        baud_rate=baud_rate,
        injected_lines=tuple(lines) if lines is not None else None,
    )
    return ManagedFrameHealthReader(
        delegate,
        InputSourceHealth(
            InputSourceHealthStatus.DISCONNECTED,
            reason="not_started",
            age_ms=0,
        ),
    )


__all__ = ["build_reader"]
