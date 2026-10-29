"""Read Darwin process-group states without launching a helper process.

XNU excludes zombies from ``killpg`` targets and returns EPERM for a group
containing only zombies. Only a complete, stable native process view can prove
that such a group has no executable members. Unavailable or changing views
remain active so the caller retains its cleanup failure and bounded deadline.
"""

from __future__ import annotations

import ctypes
import functools


# libproc.h, sys/proc_info.h and sys/proc.h in the macOS SDK define this ABI.
_PROC_PGRP_ONLY = 2
_PROC_PIDT_SHORTBSDINFO = 13
_SZOMB = 5


class _BsdShortInfo(ctypes.Structure):
    _fields_ = [
        ("pid", ctypes.c_uint32),
        ("ppid", ctypes.c_uint32),
        ("pgid", ctypes.c_uint32),
        ("status", ctypes.c_uint32),
        ("comm", ctypes.c_char * 16),
        ("flags", ctypes.c_uint32),
        ("uid", ctypes.c_uint32),
        ("gid", ctypes.c_uint32),
        ("ruid", ctypes.c_uint32),
        ("rgid", ctypes.c_uint32),
        ("svuid", ctypes.c_uint32),
        ("svgid", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
    ]


@functools.cache
def _libproc():
    # An absolute system-library path avoids search helpers and environment
    # lookups. Cache bindings only; every process observation remains fresh.
    library = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)
    library.proc_listpids.argtypes = [
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int,
    ]
    library.proc_listpids.restype = ctypes.c_int
    library.proc_pidinfo.argtypes = [
        ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int,
    ]
    library.proc_pidinfo.restype = ctypes.c_int
    return library


def _group_members(library, process_group: int) -> frozenset[int] | None:
    """Return a complete pid set, or unknown on errors or a full buffer."""
    width = ctypes.sizeof(ctypes.c_int)
    ctypes.set_errno(0)
    estimate = library.proc_listpids(_PROC_PGRP_ONLY, process_group, None, 0)
    if ctypes.get_errno() or estimate <= 0 or estimate % width:
        return None
    # The estimate includes kernel headroom. An additional slot lets an exactly
    # filled/truncated result remain unknown rather than silently lose a pid.
    pids = (ctypes.c_int * (estimate // width + 1))()
    capacity = ctypes.sizeof(pids)
    ctypes.set_errno(0)
    copied = library.proc_listpids(_PROC_PGRP_ONLY, process_group, pids, capacity)
    if ctypes.get_errno() or copied < 0 or copied >= capacity or copied % width:
        return None
    members = list(pids[:copied // width])
    if any(pid <= 0 for pid in members) or len(set(members)) != len(members):
        return None
    return frozenset(members)


def group_has_active_members(process_group: int) -> bool:
    """Keep live, unreadable, incomplete or changing groups active."""
    if not 0 < process_group < (1 << 31):
        return True
    try:
        library = _libproc()
        members = _group_members(library, process_group)
        if members is None:
            return True
        for pid in members:
            info = _BsdShortInfo()
            ctypes.set_errno(0)
            # arg=1 includes zombies in XNU's proc_find_zombref lookup. The
            # default arg=0 would incorrectly treat them as unavailable.
            copied = library.proc_pidinfo(
                pid, _PROC_PIDT_SHORTBSDINFO, 1, ctypes.byref(info), ctypes.sizeof(info),
            )
            if (ctypes.get_errno() or copied != ctypes.sizeof(info)
                    or info.pid != pid or info.pgid != process_group
                    or info.status != _SZOMB):
                return True
        return _group_members(library, process_group) != members
    except (OSError, AttributeError, OverflowError):
        return True
