"""Pure SDK/native-producer value contract; no process or native API calls."""

import ctypes
import errno
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import darwin_process


class ExitTransitionContract(unittest.TestCase):
    def test_sdk_exit_flag_field_layout(self):
        self.assertEqual(darwin_process._BsdShortInfo.flags.offset, 32)

    def observe(self, records):
        group = 42

        def listpids(kind, selected, buffer, capacity):
            self.assertEqual((kind, selected), (2, group))
            if buffer is None:
                return 64
            for index, pid in enumerate(records):
                buffer[index] = pid
            return len(records) * ctypes.sizeof(ctypes.c_int)

        def pidinfo(pid, flavor, include_zombies, buffer, capacity):
            self.assertEqual((flavor, include_zombies, capacity), (13, 1, 64))
            status, flags, error = records[pid]
            info = buffer._obj
            info.pid, info.pgid, info.status, info.flags = pid, group, status, flags
            ctypes.set_errno(error)
            return capacity

        library = SimpleNamespace(proc_listpids=listpids, proc_pidinfo=pidinfo)
        with patch.object(darwin_process, "_libproc", return_value=library):
            return darwin_process.group_state(group)

    def test_non_zombie_native_inexit_is_pending_not_terminal_live(self):
        # Apple's producer exports p_stat and P_LEXIT as independent fields.
        self.assertIs(
            self.observe({42: (2, 4, 0)}), darwin_process.GroupState.CHANGING,
        )

    def test_zombie_inexit_still_requires_complete_stable_zombie_view(self):
        self.assertIs(
            self.observe({42: (5, 4, 0)}), darwin_process.GroupState.INACTIVE,
        )

    def test_live_sibling_never_becomes_inactive(self):
        self.assertIs(
            self.observe({42: (2, 4, 0), 43: (2, 0, 0)}),
            darwin_process.GroupState.ACTIVE,
        )

    def test_inexit_does_not_override_native_permission_failure(self):
        self.assertIs(
            self.observe({42: (2, 4, errno.EPERM)}),
            darwin_process.GroupState.UNKNOWN,
        )

    def test_exiting_member_does_not_hide_denied_sibling(self):
        self.assertIs(
            self.observe({42: (2, 4, 0), 43: (2, 0, errno.EPERM)}),
            darwin_process.GroupState.UNKNOWN,
        )

    def test_exiting_members_stay_pending_even_with_zombie_sibling(self):
        self.assertIs(
            self.observe({42: (2, 4, 0), 43: (5, 4, 0)}),
            darwin_process.GroupState.CHANGING,
        )

    def test_unrelated_flags_do_not_make_live_state_transient(self):
        self.assertIs(
            self.observe({42: (2, 0x10, 0)}), darwin_process.GroupState.ACTIVE,
        )


if __name__ == "__main__":
    unittest.main()
