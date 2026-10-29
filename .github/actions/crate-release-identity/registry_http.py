"""Bound and strictly parse registry HTTP response framing."""
from __future__ import annotations

import http.client
import re
from enum import Enum, auto
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, build_opener

REGISTRY_FRAMING_BYTES = http.client._MAXLINE
REGISTRY_FRAMING_LINES = http.client._MAXHEADERS
TOKEN_BYTES = frozenset(
    b"!#$%&'*+-.^_`|~0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
)


class RegistryFramingError(http.client.HTTPException):
    """A syntactically invalid HTTP response cannot be retried as transport loss."""


class RegistryBodyDisconnect(OSError):
    """The peer disconnected before a complete response reached its terminator."""


class NoRedirect(HTTPRedirectHandler):
    """Reject redirects so registry identity never changes endpoints implicitly."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LineState(Enum):
    """Whether received bytes complete, can complete, or violate a line grammar."""

    COMPLETE = auto()
    PREFIX = auto()
    INVALID = auto()


class RegistryWireReader:
    """Read every framing byte under one aggregate byte and line budget."""

    def __init__(self, stream):
        self.stream = stream
        self.bytes_read = 0
        self.lines_read = 0

    def _capacity(self):
        if (self.bytes_read >= REGISTRY_FRAMING_BYTES
                or self.lines_read >= REGISTRY_FRAMING_LINES):
            raise RegistryFramingError("HTTP response framing exceeds the aggregate bound")
        return REGISTRY_FRAMING_BYTES - self.bytes_read

    def line(self, kind, grammar):
        remaining = self._capacity()
        capacity = min(http.client._MAXLINE, remaining)
        line = self.stream.readline(capacity)
        if not line:
            raise RegistryBodyDisconnect(f"connection closed during HTTP {kind}")
        self.bytes_read += len(line)
        self.lines_read += 1
        state = grammar(line)
        if state is LineState.COMPLETE:
            return line
        if state is LineState.INVALID:
            raise RegistryFramingError(f"malformed HTTP {kind}")
        if len(line) == capacity:
            message = ("HTTP response framing exceeds the aggregate bound"
                       if capacity == remaining else f"HTTP {kind} exceeds the line bound")
            raise RegistryFramingError(message)
        raise RegistryBodyDisconnect(f"connection closed during HTTP {kind}")

    def exact(self, expected, kind):
        remaining = self._capacity()
        capacity = min(len(expected), remaining)
        value = self.stream.read(capacity)
        self.bytes_read += len(value)
        self.lines_read += 1
        if value == expected:
            return
        if not expected.startswith(value):
            raise RegistryFramingError(f"malformed HTTP {kind}")
        if len(value) == capacity and capacity < len(expected):
            raise RegistryFramingError("HTTP response framing exceeds the aggregate bound")
        raise RegistryBodyDisconnect(f"connection closed during HTTP {kind}")

    def status(self):
        line = self.line("status line", status_line_state)
        version, status, reason = line[:-2].split(b" ", 2)
        return version, int(status), reason.decode("iso-8859-1")

    def fields(self, kind):
        fields = []
        while True:
            def grammar(value):
                return field_line_state(value, fields)

            line = self.line(kind, grammar)
            if line == b"\r\n":
                return tuple(fields)
            fields.append(validate_field_line(line, kind))


def valid_token(value):
    return bool(value) and all(byte in TOKEN_BYTES for byte in value)


def _line_state(value, payload_parser):
    """Apply one payload grammar and the shared exact CRLF grammar."""
    if value.endswith(b"\r\n"):
        payload = value[:-2]
        if b"\r" in payload or b"\n" in payload:
            return LineState.INVALID
        state = payload_parser(payload)
        return LineState.COMPLETE if state is LineState.COMPLETE else LineState.INVALID
    if b"\r" in value or b"\n" in value:
        if value.endswith(b"\r") and b"\r" not in value[:-1] and b"\n" not in value[:-1]:
            return (LineState.PREFIX
                    if payload_parser(value[:-1]) is LineState.COMPLETE
                    else LineState.INVALID)
        return LineState.INVALID
    state = payload_parser(value)
    return LineState.PREFIX if state is not LineState.INVALID else LineState.INVALID


def _status_payload_state(value):
    literal = b"HTTP/1."
    if len(value) <= len(literal):
        return LineState.PREFIX if literal.startswith(value) else LineState.INVALID
    if not value.startswith(literal) or value[len(literal)] not in b"0123456789":
        return LineState.INVALID
    remainder = value[len(literal) + 1:]
    if not remainder:
        return LineState.PREFIX
    if remainder[:1] != b" ":
        return LineState.INVALID
    remainder = remainder[1:]
    if len(remainder) < 3:
        return (LineState.PREFIX if all(byte in b"0123456789" for byte in remainder)
                else LineState.INVALID)
    if not all(byte in b"0123456789" for byte in remainder[:3]):
        return LineState.INVALID
    if len(remainder) == 3:
        return LineState.PREFIX
    if remainder[3:4] != b" ":
        return LineState.INVALID
    if any(byte != 9 and not (32 <= byte <= 126 or byte >= 128)
           for byte in remainder[4:]):
        return LineState.INVALID
    return LineState.COMPLETE


def status_line_state(value):
    """Recognize complete and completable RFC 9112 status lines."""
    return _line_state(value, _status_payload_state)


def _content_length_state(value):
    position = _consume_bws(value, 0)
    if position == len(value):
        return LineState.PREFIX
    digits = position
    while position < len(value) and value[position] in b"0123456789":
        position += 1
    if position == digits:
        return LineState.INVALID
    position = _consume_bws(value, position)
    return LineState.COMPLETE if position == len(value) else LineState.INVALID


def _transfer_encoding_state(value):
    position = _consume_bws(value, 0)
    coding = b"chunked"
    remainder = value[position:]
    prefix = remainder[:len(coding)].lower()
    if not coding.startswith(prefix):
        return LineState.INVALID
    if len(remainder) < len(coding):
        return LineState.PREFIX
    if prefix != coding:
        return LineState.INVALID
    position += len(coding)
    position = _consume_bws(value, position)
    return LineState.COMPLETE if position == len(value) else LineState.INVALID


def _field_payload_state(value, prior_fields):
    if not value:
        return LineState.COMPLETE
    name, separator, field_value = value.partition(b":")
    if not valid_token(name):
        return LineState.INVALID
    if not separator:
        return LineState.PREFIX
    if any(byte != 9 and not (32 <= byte <= 126 or byte >= 128)
           for byte in field_value):
        return LineState.INVALID
    normalized = name.lower()
    prior_names = {prior_name for prior_name, _prior_value in prior_fields}
    if normalized == b"content-length":
        if b"content-length" in prior_names or b"transfer-encoding" in prior_names:
            return LineState.INVALID
        return _content_length_state(field_value)
    if normalized == b"transfer-encoding":
        if b"content-length" in prior_names or b"transfer-encoding" in prior_names:
            return LineState.INVALID
        return _transfer_encoding_state(field_value)
    return LineState.COMPLETE


def field_line_state(value, prior_fields=()):
    """Recognize complete and completable RFC 9112 field lines."""
    return _line_state(value, lambda payload: _field_payload_state(payload, prior_fields))


def validate_field_line(line, kind):
    """Validate RFC 9112 section 5 field-line syntax without normalization."""
    if not line.endswith(b"\r\n"):
        raise RegistryFramingError(f"{kind} lacks its CRLF terminator")
    field = line[:-2]
    name, separator, value = field.partition(b":")
    if not separator or not valid_token(name):
        raise RegistryFramingError(f"malformed HTTP {kind} name")
    if any(byte != 9 and (byte < 32 or byte == 127) for byte in value):
        raise RegistryFramingError(f"malformed HTTP {kind} value")
    return name.lower(), value.strip(b" \t")


def framing_fields(fields):
    """Return validated content length and transfer coding."""
    lengths = [value for name, value in fields if name == b"content-length"]
    transfers = [value for name, value in fields if name == b"transfer-encoding"]
    if (len(lengths) > 1 or (lengths and not re.fullmatch(rb"[0-9]+", lengths[0]))
            or len(transfers) > 1 or (lengths and transfers)
            or (transfers and transfers[0].lower() != b"chunked")):
        raise RegistryFramingError("malformed or inconsistent registry HTTP framing")
    length = int(lengths[0]) if lengths else None
    return length, bool(transfers)


def message_from_fields(fields):
    message = http.client.HTTPMessage()
    for name, value in fields:
        message.add_header(name.decode("ascii"), value.decode("iso-8859-1"))
    return message


def _consume_bws(value, position):
    while position < len(value) and value[position] in (9, 32):
        position += 1
    return position


def _quoted_value_end(value, position):
    position += 1
    while position < len(value):
        byte = value[position]
        if byte == 34:
            return position + 1, LineState.COMPLETE
        if byte == 92:
            position += 1
            if position == len(value):
                return position, LineState.PREFIX
            byte = value[position]
            if byte != 9 and not (32 <= byte <= 126 or byte >= 128):
                return position, LineState.INVALID
        elif byte != 9 and byte != 32 and not (byte == 33 or 35 <= byte <= 91
                                                 or 93 <= byte <= 126 or byte >= 128):
            return position, LineState.INVALID
        position += 1
    return position, LineState.PREFIX


def _chunk_payload_state(value):
    if not value:
        return LineState.PREFIX
    position = 0
    while position < len(value) and value[position] in b"0123456789ABCDEFabcdef":
        position += 1
    if position == 0:
        return LineState.INVALID
    if position == len(value):
        return LineState.COMPLETE

    while True:
        separator_start = position
        position = _consume_bws(value, position)
        if position == len(value):
            return (LineState.COMPLETE if position == separator_start
                    else LineState.PREFIX)
        if value[position] != 59:
            return LineState.INVALID
        position = _consume_bws(value, position + 1)
        if position == len(value):
            return LineState.PREFIX
        name_start = position
        while position < len(value) and value[position] in TOKEN_BYTES:
            position += 1
        if position == name_start:
            return LineState.INVALID
        name_end = position
        position = _consume_bws(value, position)
        if position == len(value):
            return (LineState.COMPLETE if position == name_end
                    else LineState.PREFIX)
        if value[position] == 59:
            continue
        if value[position] != 61:
            return LineState.INVALID
        position = _consume_bws(value, position + 1)
        if position == len(value):
            return LineState.PREFIX
        if value[position] == 34:
            position, state = _quoted_value_end(value, position)
            if state is not LineState.COMPLETE:
                return state
        else:
            value_start = position
            while position < len(value) and value[position] in TOKEN_BYTES:
                position += 1
            if position == value_start:
                return LineState.INVALID
        value_end = position
        position = _consume_bws(value, position)
        if position == len(value):
            return (LineState.COMPLETE if position == value_end
                    else LineState.PREFIX)
        if value[position] != 59:
            return LineState.INVALID


def chunk_line_state(value):
    """Recognize complete and completable RFC 9112 chunk-size lines."""
    return _line_state(value, _chunk_payload_state)


class StrictHTTPResponse(http.client.HTTPResponse):
    """Retain stdlib connection handling with strict RFC 9112 framing."""

    def begin(self):
        if self.headers is not None:
            return
        wire = RegistryWireReader(self.fp)
        while True:
            version, status, reason = wire.status()
            fields = wire.fields("header")
            length, chunked = framing_fields(fields)
            if not 100 <= status < 200:
                break
            if length is not None or chunked:
                raise RegistryFramingError("informational response carries body framing")
            if status == http.client.SWITCHING_PROTOCOLS:
                raise RegistryFramingError("HTTP protocol switching is unsupported")
        if version == b"HTTP/1.0":
            self.version = 10
        else:
            self.version = 11
        if version == b"HTTP/1.0" and chunked:
            raise RegistryFramingError("HTTP/1.0 response uses Transfer-Encoding")
        self.code = self.status = status
        self.reason = reason.strip()
        self.atlas_fields = fields
        self.headers = self.msg = message_from_fields(fields)
        self.chunked = chunked
        self.chunk_left = None
        self.will_close = self._check_close()
        self.length = None if chunked else length
        if (status == http.client.NO_CONTENT or status == http.client.NOT_MODIFIED
                or self._method == "HEAD"):
            self.length = 0
        if not self.will_close and not self.chunked and self.length is None:
            self.will_close = True
        self._atlas_wire = wire

    def _read_next_chunk_size(self):
        line = self._atlas_wire.line("chunk size", chunk_line_state)
        size = re.match(rb"[0-9A-Fa-f]+", line)
        return int(size.group(), 16)

    def _get_chunk_left(self):
        chunk_left = self.chunk_left
        if not chunk_left:
            if chunk_left is not None:
                self._atlas_wire.exact(b"\r\n", "chunk data delimiter")
            chunk_left = self._read_next_chunk_size()
            if chunk_left == 0:
                self._read_and_discard_trailer()
                self._close_conn()
                chunk_left = None
            self.chunk_left = chunk_left
        return chunk_left

    def _read_and_discard_trailer(self):
        while True:
            line = self._atlas_wire.line("trailer", field_line_state)
            if line == b"\r\n":
                return
            validate_field_line(line, "trailer")


class StrictHTTPConnection(http.client.HTTPConnection):
    response_class = StrictHTTPResponse


class StrictHTTPSConnection(http.client.HTTPSConnection):
    response_class = StrictHTTPResponse


class StrictHTTPHandler(HTTPHandler):
    def http_open(self, request):
        return self.do_open(StrictHTTPConnection, request)


class StrictHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(StrictHTTPSConnection, request, context=self._context)


def open_response(request, timeout):
    """Open one response without following redirects."""
    return build_opener(NoRedirect(), StrictHTTPHandler(), StrictHTTPSHandler()).open(
        request, timeout=timeout
    )
