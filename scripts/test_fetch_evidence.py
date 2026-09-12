"""Packaging checks kept outside the frozen evaluator's tests/*.py source inventory."""

import hashlib
import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from fetch_evidence import extract


class EvidenceDownloadTests(unittest.TestCase):
    def test_round_trip_integrity_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, expected = self.archive(root, "artifacts/study/result.json")
            output = root / "download"
            (output / "local-run").mkdir(parents=True)
            (output / "local-run/keep.txt").write_text("local result")
            extract(archive, output, expected)
            self.assertEqual((output / "local-run/keep.txt").read_text(), "local result")
            self.assertEqual((output / "study/result.json").read_bytes(), b"{}")
            with self.assertRaises(FileExistsError):
                extract(archive, output, expected)
            with self.assertRaises(ValueError):
                extract(archive, root / "bad-checksum", {**expected, "sha256": "0" * 64})
            self.assertFalse((root / "bad-checksum").exists())

    def test_rejects_unsafe_entries_and_wrong_inventory_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, kind in [
                ("artifacts/study/../../escape", tarfile.REGTYPE),
                ("/absolute", tarfile.REGTYPE),
                ("artifacts/unknown/result.json", tarfile.REGTYPE),
                ("artifacts/study/link", tarfile.SYMTYPE),
            ]:
                with self.subTest(name=name):
                    archive, expected = self.archive(root, name, kind)
                    with self.assertRaises(ValueError):
                        extract(archive, root / "output", expected)
                    self.assertFalse((root / "output").exists())
            archive, expected = self.archive(root, "artifacts/study/result.json")
            for changed in [{"file_count": 2}, {"unpacked_bytes": 999}]:
                with self.assertRaises(ValueError):
                    extract(archive, root / "output", {**expected, **changed})

    @staticmethod
    def archive(root, name, kind=tarfile.REGTYPE):
        archive = root / "evidence.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = 2 if kind == tarfile.REGTYPE else 0
            member.linkname = "../../outside" if kind == tarfile.SYMTYPE else ""
            bundle.addfile(member, io.BytesIO(b"{}"))
        return archive, {
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "archive_bytes": archive.stat().st_size,
            "unpacked_bytes": member.size,
            "file_count": 1,
            "directories": ["study"],
        }


if __name__ == "__main__":
    unittest.main()
