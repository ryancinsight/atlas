"""Resolve Cargo's home from the build environment and working directory."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

_ERROR_INSUFFICIENT_BUFFER = 122


def _environment_value(environment: Mapping[str, str], name: str) -> str | None:
    if os.name != "nt":
        return environment.get(name)
    matches = [value for key, value in environment.items() if key.casefold() == name.casefold()]
    if len(matches) > 1:
        raise ValueError(f"Windows environment contains multiple spellings of {name}")
    return matches[0] if matches else None


def _windows_profile_directory() -> Path:
    import ctypes
    from ctypes import wintypes

    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    get_profile = userenv.GetUserProfileDirectoryW
    get_profile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    get_profile.restype = wintypes.BOOL
    token = wintypes.HANDLE(-4)
    size = wintypes.DWORD()
    get_profile(token, None, ctypes.byref(size))
    error = ctypes.get_last_error()
    if error != _ERROR_INSUFFICIENT_BUFFER or size.value == 0:
        raise ctypes.WinError(error)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not get_profile(token, buffer, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    return Path(buffer.value)


def _user_home(environment: Mapping[str, str]) -> Path:
    variable = "USERPROFILE" if os.name == "nt" else "HOME"
    configured = _environment_value(environment, variable)
    if configured:
        return Path(configured)
    if os.name == "nt":
        return _windows_profile_directory()
    import pwd

    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def cargo_home(
    environment: Mapping[str, str] | None = None, execution_root: Path | None = None
) -> Path:
    """Return Cargo's home for the supplied environment and command directory."""
    source = os.environ if environment is None else environment
    configured = _environment_value(source, "CARGO_HOME")
    candidate = Path(configured) if configured else _user_home(source) / ".cargo"
    if "\0" in str(candidate):
        raise ValueError("Cargo home contains a null character")
    if os.name == "nt" and candidate.drive and not candidate.root:
        raise ValueError(f"Cargo home is drive-relative: {candidate}")
    command_root = execution_root or Path.cwd()
    if not command_root.is_absolute():
        raise ValueError(f"Cargo command directory is relative: {command_root}")
    return candidate if candidate.is_absolute() else command_root / candidate
