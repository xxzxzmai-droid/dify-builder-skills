#!/usr/bin/env python3
"""Prepare a Dify plugin directory for air-gapped installation.

This script is stdlib-only and does not download dependencies. Use
fetch_offline_wheels.sh when the development machine can reach PyPI, or pass a
verified wheels directory from a plugin that already installs on the target
intranet Dify server.
"""
import argparse
import shutil
import sys
from pathlib import Path


DEFAULT_REQUIREMENT = "dify_plugin==0.4.1"


def wheel_source(path):
    source = Path(path).expanduser().resolve()
    if (source / "wheels").is_dir():
        source = source / "wheels"
    if not source.is_dir():
        raise SystemExit(f"wheels source is not a directory: {source}")
    wheels = sorted(source.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no .whl files found in wheels source: {source}")
    return source, wheels


def write_offline_requirements(plugin_dir, requirement):
    (plugin_dir / "requirements.txt").write_text(
        "--no-index\n"
        "--find-links=./wheels/\n"
        f"{requirement}\n",
        encoding="utf-8",
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare a Dify plugin for offline installation.")
    parser.add_argument("plugin_dir", help="Plugin directory to update")
    parser.add_argument("--wheels-from", help="Directory containing *.whl files or a plugin dir with wheels/")
    parser.add_argument("--requirement", default=DEFAULT_REQUIREMENT, help="Pinned dify_plugin requirement")
    args = parser.parse_args(argv)

    plugin_dir = Path(args.plugin_dir).expanduser().resolve()
    if not (plugin_dir / "manifest.yaml").is_file():
        raise SystemExit(f"plugin_dir must contain manifest.yaml: {plugin_dir}")

    wheels_dir = plugin_dir / "wheels"
    wheels_dir.mkdir(exist_ok=True)

    copied = 0
    if args.wheels_from:
        source, wheels = wheel_source(args.wheels_from)
        for wheel in wheels:
            shutil.copy2(wheel, wheels_dir / wheel.name)
            copied += 1

    wheels = sorted(wheels_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(
            "offline wheels are required. Run fetch_offline_wheels.sh on an internet-connected "
            "machine, or pass --wheels-from /path/to/verified/wheels"
        )

    write_offline_requirements(plugin_dir, args.requirement)
    print(f"offline requirements written: {plugin_dir / 'requirements.txt'}")
    print(f"wheels ready: {len(wheels)} ({copied} copied)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
