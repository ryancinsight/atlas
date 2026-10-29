"""Bound and strictly parse registry HTTP response framing."""
from __future__ import annotations

import http.client
import re
from urllib.request import HTTPHandler, HTTPRedirectHandler, HTTPSHandler, build_opener

REGISTRY_FRAMING_BYTES = http.client._MAXLINE
REGISTRY_FRAMING_LINES = http.client._MAXHEADERS
STATUS_LINE = re.compile(rb"HTTP/1\.[0-9] [0-9]{3} [\t\x20-\x7e\x80-\xff]*\r\n\Z")
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


class RegistryWireReader:
    """Read response metadata under one aggregate wire budget."""

    def __init__(self, stream):
        self.stream = stream
        self.bytes_read = 0
        self.lines_read = 0

    def line(self, kind, valid_prefix):
        if (self.bytes_read >= REGISTRY_FRAMING_BYTES
                or self.lines_read >= REGISTRY_FRAMING_LINES):
            raise RegistryFramingError("HTTP response metadata exceeds the aggregate bound")
        remaining = REGISTRY_FRAMING_BYTES - self.bytes_read
        capacity = min(http.client._MAXLINE, remaining)
        line = self.stream.readline(capacity)
        if not line:
            raise RegistryBodyDisconnect(f"connection closed during HTTP {kind}")
        self.bytes_read += len(line)
        self.lines_read += 1
        if not line.endswith(b"\r\n"):
            if len(line) == capacity:
                message = ("HTTP response metadata exceeds the aggregate bound"
                           if capacity == remaining else f"HTTP {kind} exceeds the line bound")
                raise RegistryFramingError(message)
            if valid_prefix(line):
                raise RegistryBodyDisconnect(f"connection closed during HTTP {kind}")
            raise RegistryFramingError(f"malformed HTTP {kind}")
        return line

    def status(self):
        line = self.line("status line", valid_status_prefix)
        if not STATUS_LINE.fullmatch(line):
            raise RegistryFramingError("malformed HTTP status line")
        version, status, reason = line[:-2].split(b" ", 2)
        return version, int(status), reason.decode("iso-8859-1")

    def fields(self, kind):
        fields = []
        while True:
            line = self.line(kind, valid_field_prefix)
            if line == b"\r\n":
                return tuple(fields)
            fields.append(validate_field_line(line, kind))


def valid_token(value):
    return bool(value) and all(byte in TOKEN_BYTES for byte in value)


def valid_status_prefix(value):
    """Return whether EOF interrupted a syntactically valid status prefix."""
    literal = b"HTTP/1."
    if len(value) <= len(literal):
        return literal.startswith(value)
    if not value.startswith(literal) or value[len(literal)] not in b"0123456789":
        return False
    remainder = value[len(literal) + 1:]
    if not remainder:
        return True
    if remainder[:1] != b" ":
        return False
    remainder = remainder[1:]
    digits = 0
    while digits < len(remainder) and remainder[digits] in b"0123456789":
        digits += 1
    if digits < min(3, len(remainder)):
        return False
    if len(remainder) <= 3:
        return True
    return (digits == 3 and remainder[3:4] == b" "
            and all(byte == 9 or 32 <= byte <= 126 or byte >= 128
                    for byte in remainder[4:]))


def valid_field_prefix(value):
    """Return whether EOF interrupted a syntactically valid field prefix."""
    name, separator, field_value = value.partition(b":")
    if not valid_token(name):
        return False
    if not separator:
        return True
    return all(byte != 13 and byte != 10 and
               (byte == 9 or 32 <= byte <= 126 or byte >= 128)
               for byte in field_value)


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


def valid_quoted_string(value):
    if len(value) < 2 or value[:1] != b'"' or value[-1:] != b'"':
        return False
    position = 1
    end = len(value) - 1
    while position < end:
        byte = value[position]
        if byte == 92:
            position += 1
            if position == end:
                return False
            byte = value[position]
            if byte != 9 and not (32 <= byte <= 126 or byte >= 128):
                return False
        elif byte != 9 and byte != 32 and not (byte == 33 or 35 <= byte <= 91
                                                 or 93 <= byte <= 126 or byte >= 128):
            return False
        position += 1
    return True


def valid_chunk_extensions(value):
    """Validate RFC 9112 section 7.1.1 chunk-ext grammar."""
    position = 0
    while position < len(value):
        while position < len(value) and value[position] in (9, 32):
            position += 1
        if position == len(value) or value[position] != 59:
            return False
        position += 1
        while position < len(value) and value[position] in (9, 32):
            position += 1
        if position == len(value):
            return False
        start = position
        while position < len(value) and value[position] in TOKEN_BYTES:
            position += 1
        if not valid_token(value[start:position]):
            return False
        name_end = position
        while position < len(value) and value[position] in (9, 32):
            position += 1
        if position == len(value):
            return position == name_end
        if value[position] == 61:
            position += 1
            while position < len(value) and value[position] in (9, 32):
                position += 1
            if position == len(value):
                return False
            if value[position] == 34:
                start = position
                position += 1
                while position < len(value):
                    if value[position] == 92:
                        position += 2
                        continue
                    position += 1
                    if value[position - 1] == 34:
                        break
                if not valid_quoted_string(value[start:position]):
                    return False
            else:
                start = position
                while position < len(value) and value[position] in TOKEN_BYTES:
                    position += 1
                if not valid_token(value[start:position]):
                    return False
        elif value[position] != 59:
            return False
    return True


def valid_chunk_size_prefix(value):
    """Return whether EOF interrupted a syntactically valid chunk-size prefix."""
    match = re.match(rb"[0-9A-Fa-f]+", value)
    if match is None:
        return False
    remainder = value[match.end():]
    if not remainder:
        return True
    stripped = remainder.lstrip(b" \t")
    return not stripped or stripped.startswith(b";")


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
        line = self.fp.readline(http.client._MAXLINE)
        if not line:
            raise RegistryBodyDisconnect("connection closed before the next chunk size")
        if not line.endswith(b"\r\n"):
            self._close_conn()
            if len(line) < http.client._MAXLINE and valid_chunk_size_prefix(line):
                raise RegistryBodyDisconnect("connection closed during HTTP chunk size")
            raise RegistryFramingError("malformed HTTP chunk size")
        match = re.fullmatch(rb"([0-9A-Fa-f]+)(.*)", line[:-2])
        if match is None:
            self._close_conn()
            raise RegistryFramingError("malformed HTTP chunk size")
        size, extensions = match.groups()
        if extensions and not valid_chunk_extensions(extensions):
            self._close_conn()
            raise RegistryFramingError("malformed HTTP chunk extension")
        return int(size, 16)

    def _get_chunk_left(self):
        chunk_left = self.chunk_left
        if not chunk_left:
            if chunk_left is not None:
                if self._safe_read(2) != b"\r\n":
                    self._close_conn()
                    raise RegistryFramingError("chunk data lacks its CRLF delimiter")
            chunk_left = self._read_next_chunk_size()
            if chunk_left == 0:
                self._read_and_discard_trailer()
                self._close_conn()
                chunk_left = None
            self.chunk_left = chunk_left
        return chunk_left

    def _read_and_discard_trailer(self):
        while True:
            line = self._atlas_wire.line("trailer", valid_field_prefix)
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
