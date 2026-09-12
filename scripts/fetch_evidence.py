"""Download the recorded experiment archive; no model calls or extra dependencies."""

import argparse
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def extract(archive: Path, output: Path, expected: dict) -> None:
    """Verify before extraction, and preserve any existing local experiment directory."""
    if output.is_file() or any((output / name).exists() for name in expected["directories"]):
        raise FileExistsError(
            f"Recorded evidence already exists in {output}; verify it or choose another --output"
        )
    with archive.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if archive.stat().st_size != expected["archive_bytes"] or digest != expected["sha256"]:
        raise ValueError("Evidence archive size or SHA-256 does not match reports/evidence.json")
    with tarfile.open(archive, "r:gz") as bundle:
        members = bundle.getmembers()
        names = {member.name for member in members}
        if len(names) != len(members) or len(members) != expected["file_count"]:
            raise ValueError("Evidence archive has an unexpected file inventory")
        if sum(member.size for member in members) != expected["unpacked_bytes"]:
            raise ValueError("Evidence archive has an unexpected unpacked size")
        for member in members:
            path = PurePosixPath(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
                or member.name != path.as_posix()
                or len(path.parts) < 3
                or path.parts[0] != "artifacts"
                or path.parts[1] not in expected["directories"]
            ):
                raise ValueError(f"Unexpected archive entry: {member.name}")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
            bundle.extractall(temporary, filter="data")
            output.mkdir(exist_ok=True)
            for directory in (Path(temporary) / "artifacts").iterdir():
                directory.rename(output / directory.name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts")
    args = parser.parse_args()
    expected = json.loads((ROOT / "reports/evidence.json").read_text())
    if any((args.output / name).exists() for name in expected["directories"]):
        parser.error(
            f"Recorded evidence already exists in {args.output}; verify it or choose another --output"
        )
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "evidence.tar.gz"
        with urlopen(expected["url"], timeout=60) as response:
            archive.write_bytes(response.read(expected["archive_bytes"] + 1))
        extract(archive, args.output, expected)
    for example in expected["examples"]:
        original = args.output / example["source"]
        retained = ROOT / example["path"]
        if original.read_bytes() != retained.read_bytes():
            raise ValueError(f"Retained example differs from the archive: {example['path']}")
    print(f"Verified and extracted {expected['file_count']} evidence files to {args.output}")


if __name__ == "__main__":
    main()
