#!/usr/bin/env python3
"""Canonicalize Debian package archive metadata for reproducible-build comparison.

This does not rewrite application payload bytes. It extracts the package, applies
SOURCE_DATE_EPOCH to filesystem timestamps, and rebuilds the .deb with normalized
ownership. The reproducibility gate still compares the final package SHA-256.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import tempfile


def run(command: list[str], *, env: dict[str, str]) -> None:
    subprocess.run(command, check=True, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)


def canonicalize(source: pathlib.Path, destination: pathlib.Path, epoch: int) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file() or source.suffix != ".deb":
        raise ValueError(f"source must be an existing .deb file: {source}")
    if source == destination:
        raise ValueError("source and destination must differ")
    destination.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"SOURCE_DATE_EPOCH": str(epoch), "TZ": "UTC", "LC_ALL": "C"})
    with tempfile.TemporaryDirectory(prefix="louksna-deb-normalize-") as temp:
        root = pathlib.Path(temp)
        data_dir = root / "data"
        control_dir = root / "control"
        rebuilt = root / "normalized.deb"
        data_dir.mkdir()
        control_dir.mkdir()
        run(["dpkg-deb", "--extract", str(source), str(data_dir)], env=env)
        run(["dpkg-deb", "--control", str(source), str(control_dir)], env=env)
        for base in (data_dir, control_dir):
            entries = sorted(base.rglob("*"), key=lambda p: len(p.parts), reverse=True)
            for path in entries:
                try:
                    os.utime(path, (epoch, epoch), follow_symlinks=False)
                except (NotImplementedError, PermissionError) as exc:
                    raise RuntimeError(f"could not normalize timestamp for {path}: {exc}") from exc
            os.utime(base, (epoch, epoch), follow_symlinks=False)
        run(["dpkg-deb", "--build", "--root-owner-group", str(data_dir), str(rebuilt)], env=env)
        # dpkg-deb --build uses the sibling control directory when building a
        # package root; place the control files into DEBIAN before rebuilding.
        # This second build is intentionally done below after a complete tree is staged.
        staged = root / "package-root"
        shutil.copytree(data_dir, staged, symlinks=True)
        (staged / "DEBIAN").mkdir()
        for item in control_dir.iterdir():
            target = staged / "DEBIAN" / item.name
            if item.is_dir():
                shutil.copytree(item, target, symlinks=True)
            else:
                shutil.copy2(item, target, follow_symlinks=False)
        for path in sorted(staged.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            os.utime(path, (epoch, epoch), follow_symlinks=False)
        os.utime(staged, (epoch, epoch), follow_symlinks=False)
        run(["dpkg-deb", "--build", "--root-owner-group", str(staged), str(rebuilt)], env=env)
        shutil.copyfile(rebuilt, destination)
    print(f"canonicalized={destination}")
    print(f"source_sha256={__import__('hashlib').sha256(source.read_bytes()).hexdigest()}")
    print(f"output_sha256={__import__('hashlib').sha256(destination.read_bytes()).hexdigest()}")
    print(f"output_size_bytes={destination.stat().st_size}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--source-date-epoch", required=True, type=int)
    args = parser.parse_args()
    canonicalize(args.package, args.output, args.source_date_epoch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
