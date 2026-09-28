"""Bound subprocess output without buffering untrusted output without limit."""

from __future__ import annotations

import os
import selectors
import threading
import time
from typing import BinaryIO

READ_CHUNK_BYTES = 64 * 1024
DEFAULT_CAPTURE_LIMIT_BYTES = 64 * 1024 * 1024
CAPTURE_POLL_SECONDS = 0.05


class CaptureLimitExceeded(OSError):
    """A subprocess emitted more output than the configured capture budget."""


class BoundedOutputCapture:
    """Drain two subprocess pipes while retaining at most one shared byte budget."""

    def __init__(
        self,
        stdout: BinaryIO,
        stderr: BinaryIO,
        limit_bytes: int = DEFAULT_CAPTURE_LIMIT_BYTES,
    ) -> None:
        if limit_bytes <= 0:
            raise ValueError("capture limit must be positive")
        self._streams = {"stdout": stdout, "stderr": stderr}
        self._limit_bytes = limit_bytes
        self._total_bytes = 0
        self._buffers = {"stdout": bytearray(), "stderr": bytearray()}
        self._lock = threading.Lock()
        self._limit_reached = threading.Event()
        self._reader_error: OSError | None = None
        self._changed = threading.Event()
        self._closed_streams: set[str] = set()
        self._selector: selectors.BaseSelector | None = None
        self._threads: tuple[threading.Thread, ...] = ()
        self._closed = False

        if os.name == "nt":
            self._threads = tuple(
                threading.Thread(
                    target=self._drain_thread,
                    args=(name, stream),
                    name=f"atlas-capture-{name}",
                    daemon=False,
                )
                for name, stream in self._streams.items()
            )
            for thread in self._threads:
                thread.start()
        else:
            selector = selectors.DefaultSelector()
            for name, stream in self._streams.items():
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            self._selector = selector

    def check(self) -> None:
        if self._limit_reached.is_set():
            raise CaptureLimitExceeded(
                f"subprocess output exceeded the {self._limit_bytes}-byte capture limit"
            )
        if self._reader_error is not None:
            raise OSError(f"cannot read subprocess output: {self._reader_error}") from self._reader_error

    def wait(self, timeout: float) -> None:
        if os.name == "nt":
            self._changed.wait(timeout)
            self._changed.clear()
            self.check()
            return
        selector = self._selector
        if selector is None:
            raise OSError("subprocess output capture is closed")
        for key, _ in selector.select(timeout):
            name = str(key.data)
            stream = self._streams[name]
            while True:
                try:
                    chunk = os.read(stream.fileno(), READ_CHUNK_BYTES)
                except BlockingIOError:
                    break
                except OSError as error:
                    self._reader_error = error
                    break
                if not chunk:
                    selector.unregister(stream)
                    self._closed_streams.add(name)
                    break
                self._append(name, chunk)
                if self._limit_reached.is_set():
                    break
        self.check()

    def finish(
        self,
        timeout: float,
        *,
        tolerate_limit: bool = False,
    ) -> tuple[bytes, bytes]:
        deadline = time.monotonic() + timeout
        try:
            if os.name == "nt":
                for thread in self._threads:
                    thread.join(max(0.0, deadline - time.monotonic()))
                if any(thread.is_alive() for thread in self._threads):
                    raise OSError("subprocess output pipes remained open after cleanup")
            else:
                while len(self._closed_streams) != len(self._streams):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0.0:
                        raise OSError("subprocess output pipes remained open after cleanup")
                    self.wait(min(CAPTURE_POLL_SECONDS, remaining))
            if not tolerate_limit:
                self.check()
            elif self._reader_error is not None:
                raise OSError(
                    f"cannot drain subprocess output after cleanup: {self._reader_error}"
                ) from self._reader_error
            output = bytes(self._buffers["stdout"]), bytes(self._buffers["stderr"])
        except BaseException as error:
            close_error = self.close()
            if close_error is not None:
                raise error from close_error
            raise
        close_error = self.close()
        if close_error is not None:
            raise OSError("cannot close subprocess output pipes") from close_error
        return output

    def close(self) -> OSError | None:
        if self._closed:
            return None
        self._closed = True
        if self._selector is not None:
            self._selector.close()
            self._selector = None
        failure: OSError | None = None
        for stream in self._streams.values():
            try:
                stream.close()
            except OSError as error:
                failure = failure or error
        return failure

    def _append(self, name: str, chunk: bytes) -> None:
        with self._lock:
            remaining = self._limit_bytes - self._total_bytes
            accepted = min(remaining, len(chunk))
            if accepted:
                self._buffers[name].extend(chunk[:accepted])
                self._total_bytes += accepted
            if accepted != len(chunk):
                self._limit_reached.set()
                self._changed.set()

    def _drain_thread(self, name: str, stream: BinaryIO) -> None:
        try:
            while True:
                chunk = stream.read(READ_CHUNK_BYTES)
                if not chunk:
                    return
                self._append(name, chunk)
                if self._limit_reached.is_set():
                    self._changed.set()
        except OSError as error:
            self._reader_error = error
            self._changed.set()

