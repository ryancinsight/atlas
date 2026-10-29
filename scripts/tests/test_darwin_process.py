"""Pin the native libproc ABI and fail-closed process-state decisions."""

import ctypes
import errno
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import darwin_process


class DarwinProcessTests(unittest.TestCase):
    def test_sdk_short_info_layout(self):
        self.assertEqual(ctypes.sizeof(darwin_process._BsdShortInfo), 64)
        for field, offset in (("pid", 0), ("pgid", 8), ("status", 12), ("comm", 16), ("reserved", 60)):
            with self.subTest(field=field):
                self.assertEqual(getattr(darwin_process._BsdShortInfo, field).offset, offset)

    def observe(self, *, members=(42,), after=None, state=5, pid=42, group=42,
                list_error=0, info_error=0, info_size=64, full=False,
                estimate=64, odd=False):
        reads = []

        def listpids(kind, selected_group, buffer, capacity):
            self.assertEqual((kind, selected_group), (2, 42))
            self.assertEqual(ctypes.get_errno(), 0)
            ctypes.set_errno(list_error)
            if buffer is None:
                self.assertEqual(capacity, 0)
                return estimate
            rows = members if not reads or after is None else after
            reads.append(rows)
            for index, member in enumerate(rows):
                buffer[index] = member
            return capacity if full else len(rows) * ctypes.sizeof(ctypes.c_int) + int(odd)

        def pidinfo(selected_pid, flavor, include_zombies, buffer, capacity):
            self.assertEqual((selected_pid, flavor, include_zombies, capacity), (42, 13, 1, 64))
            self.assertEqual(ctypes.get_errno(), 0)
            info = buffer._obj
            info.pid, info.pgid, info.status = pid, group, state
            ctypes.set_errno(info_error)
            return info_size

        library = SimpleNamespace(proc_listpids=listpids, proc_pidinfo=pidinfo)
        # A previous native operation's errno must not taint a fresh read.
        ctypes.set_errno(errno.EPERM)
        with patch.object(darwin_process, "_libproc", return_value=library):
            return darwin_process.group_has_active_members(42)

    def test_only_complete_stable_empty_or_zombie_views_are_inactive(self):
        self.assertFalse(self.observe())
        self.assertFalse(self.observe(members=()))
        for case in (
            {"state": 2}, {"state": 0}, {"group": 43}, {"pid": 43},
            {"info_size": 0}, {"info_size": 63}, {"info_size": 65},
            {"info_error": errno.EPERM}, {"info_error": errno.ESRCH},
            {"list_error": errno.EPERM}, {"estimate": 0}, {"estimate": -1},
            {"estimate": 63}, {"full": True}, {"odd": True},
            {"members": (0,)}, {"members": (-1,)}, {"members": (42, 42)},
            {"after": ()}, {"after": (42, 43)},
            {"members": (), "after": (43,)},
        ):
            with self.subTest(case=case):
                self.assertTrue(self.observe(**case))

    def test_unavailable_library_and_invalid_groups_remain_active(self):
        for error in (OSError("unavailable"), AttributeError("missing native API")):
            with self.subTest(error=error), patch.object(darwin_process, "_libproc", side_effect=error):
                self.assertTrue(darwin_process.group_has_active_members(42))
        with patch.object(darwin_process, "_libproc") as load:
            for group in (-1, 0, 1 << 31):
                self.assertTrue(darwin_process.group_has_active_members(group))
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
