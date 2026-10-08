"""Offline restore checks. No serial ports or physical devices are opened."""

import contextlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fm1t


ROOT = Path(__file__).resolve().parents[2]


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.package = ROOT / "FM-1.fwsc"
        self.image, _ = fm1t.package_image(self.package)
        self.ref = bytearray(self.image + bytes([0xA5]) * (fm1t.FLASH_SIZE - len(self.image)))
        for a in range(fm1t.WRITE_MIN, fm1t.APP_END, fm1t.SECTOR):
            self.ref[a] ^= 1
        self.ref_path = Path(self.temp.name) / "backup.bin"
        self.ref_path.write_bytes(self.ref)
        self.args = SimpleNamespace(package=self.package, ref=self.ref_path, write=True)
        self.now = bytes(self.ref)
        self.ensure = self.enterContext(patch.object(fm1t, "ensure_uboot"))
        self.request = self.enterContext(patch.object(fm1t, "request", return_value="OK key=980F type=3 id=856014"))
        self.read = self.enterContext(patch.object(fm1t, "read_flash"))
        self.write = self.enterContext(patch.object(fm1t, "write_sector", return_value="OK"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def run_restore(self, final=None):
        self.read.side_effect = [self.now, final if final is not None else self.image + self.now[len(self.image):]]
        fm1t.cmd_write(object(), self.args)

    def test_package_matches_independently_extracted_image(self):
        self.assertEqual(self.image, (ROOT / "firmware-inspection/flash.bin").read_bytes())

    def test_modified_truncated_and_unknown_packages_refused(self):
        data = self.package.read_bytes()
        bad = Path(self.temp.name) / "bad.fwsc"
        for payload in (data[:-1], data + b"\0", bytes([data[0] ^ 1]) + data[1:], b"unknown"):
            with self.subTest(size=len(payload)):
                bad.write_bytes(payload)
                self.args.package = bad
                with self.assertRaisesRegex(SystemExit, "not the verified stock V15"):
                    self.run_restore()
                self.ensure.assert_not_called()
                self.write.assert_not_called()

    def test_dry_run_reads_once_and_never_writes(self):
        self.args.write = False
        self.run_restore()
        self.read.assert_called_once()
        self.write.assert_not_called()

    def test_restore_only_application_and_preserves_fresh_device_data(self):
        self.now = self.now[:fm1t.APP_END] + bytes([0x5A]) * (fm1t.FLASH_SIZE - fm1t.APP_END)
        self.run_restore()
        self.assertEqual(self.read.call_count, 2)
        calls = self.write.call_args_list
        self.assertEqual([c.args[1] for c in calls], list(range(0x4000, 0x93000, 0x1000)))
        for c in calls:
            a, sector = c.args[1:]
            self.assertEqual(sector, self.image[a:a + fm1t.SECTOR])

    def test_bad_reference_size_and_protected_boot_refused(self):
        for ref in (self.ref[:-1], bytes([self.ref[0] ^ 1]) + self.ref[1:]):
            self.ref_path.write_bytes(ref)
            with self.assertRaises(SystemExit):
                self.run_restore()
            self.ensure.assert_not_called()
            self.write.assert_not_called()

    def test_wrong_chip_refused(self):
        self.request.return_value = "OK key=0000 type=3 id=856014"
        with self.assertRaisesRegex(SystemExit, "chip key / flash id mismatch"):
            self.run_restore()
        self.read.assert_not_called()
        self.write.assert_not_called()

    def test_changed_live_application_refused(self):
        changed = bytearray(self.now)
        changed[0x8000] ^= 1
        self.now = bytes(changed)
        with self.assertRaisesRegex(SystemExit, "flash differs from --ref"):
            self.run_restore()
        self.write.assert_not_called()

    def test_write_failure_stops_immediately(self):
        self.write.return_value = "ERR verify"
        with self.assertRaisesRegex(SystemExit, "sector write failed"):
            self.run_restore()
        self.write.assert_called_once()
        self.read.assert_called_once()

    def test_final_read_detects_boot_application_and_device_data_corruption(self):
        expected = self.image + self.now[len(self.image):]
        for a in (0, 0x4000, 0x93000):
            with self.subTest(address=hex(a)):
                bad = bytearray(expected)
                bad[a] ^= 1
                with self.assertRaisesRegex(SystemExit, "final read DIFFERS"):
                    self.run_restore(bytes(bad))


if __name__ == "__main__":
    unittest.main()
