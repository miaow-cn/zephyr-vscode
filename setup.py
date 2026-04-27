#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage()
        self.exit(2, f"{self.prog}: Run with -h for full help.\n")


def parse_args() -> argparse.Namespace:
    parser = _Parser(
        description=(
            "Post-build VS Code integration script for Zephyr projects. "
            "Updates .vscode/launch.json with the current toolchain/device info "
            "and refreshes the .vscode/build symlink to the active build directory. "
            "Intended to be called automatically by CMake after the final ELF is linked."
        ),
    )
    parser.add_argument(
        "--app-path",
        required=True,
        metavar="DIR",
        help="Absolute path to the Zephyr application source directory (CMAKE_CURRENT_SOURCE_DIR).",
    )
    parser.add_argument(
        "--build-path",
        required=True,
        metavar="DIR",
        help="Absolute path to the CMake build directory (CMAKE_BINARY_DIR).",
    )
    parser.add_argument(
        "--toolchain-path",
        required=True,
        metavar="DIR",
        help="Directory containing the ARM GDB binary (e.g. .../arm-zephyr-eabi/bin).",
    )
    parser.add_argument(
        "--gdb-path",
        required=True,
        metavar="FILE",
        help="Full path to the GDB executable (CMAKE_GDB).",
    )
    parser.add_argument(
        "--device",
        required=True,
        metavar="DEVICE",
        help=(
            "J-Link device string written into launch.json. "
            "For boards with external flash use the extended form: "
            "DEVICE?BankAddr=0x...&Loader=..."
        ),
    )
    parser.add_argument(
        "--launch-json",
        required=True,
        metavar="FILE",
        help="Absolute path to the .vscode/launch.json file to update.",
    )
    return parser.parse_args()


def infer_toolchain_prefix(gdb_path: Path) -> str:
    name = gdb_path.name
    for suffix in ("gdb-py", "gdb"):
        if name.endswith(suffix):
            prefix = name[: -len(suffix)]
            return prefix[:-1] if prefix.endswith("-") else prefix
    return ""


def update_symlink(vscode_dir: Path, build_path: Path) -> None:
    link_path = vscode_dir / "build"
    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()
    os.symlink(build_path, link_path)
    print(f"setup.py: {link_path} -> {build_path}")


def update_launch_json(
    launch_json: Path,
    toolchain_path: str,
    gdb_path: str,
    device: str,
    toolchain_prefix: str,
) -> None:
    with launch_json.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    for config in data.get("configurations", []):
        if config.get("type") != "cortex-debug":
            continue

        config["executable"] = "${workspaceFolder}/.vscode/build/zephyr/zephyr.elf"
        config["armToolchainPath"] = toolchain_path
        config["gdbPath"] = gdb_path
        if toolchain_prefix:
            config["toolchainPrefix"] = toolchain_prefix
        config["device"] = device

    with launch_json.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
        handle.write("\n")
    
    print(f"setup.py: updated {launch_json}")
    assume_unchanged(launch_json)

def assume_unchanged(file_name: Path) -> None:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    result = subprocess.run(
        ["git", "update-index", "--assume-unchanged", str(file_name)],
        cwd=script_dir,
        capture_output=True,
        text=True
    )
    print(f"setup.py: {file_name} is now assumed unchanged by git. ")
    print(f"\tIf you want to track changes again, run: git update-index --no-assume-unchanged {file_name}")


def main() -> int:
    args = parse_args()

    app_path = Path(args.app_path).resolve()
    build_path = Path(args.build_path).resolve()
    toolchain_path = Path(args.toolchain_path).resolve()
    gdb_path = Path(args.gdb_path).resolve()
    launch_json = Path(args.launch_json).resolve()
    vscode_dir = launch_json.parent

    if not app_path.is_dir():
        raise SystemExit(f"setup.py: app path not found: {app_path}")
    if not build_path.is_dir():
        raise SystemExit(f"setup.py: build path not found: {build_path}")
    if not toolchain_path.is_dir():
        raise SystemExit(f"setup.py: toolchain path not found: {toolchain_path}")
    if not gdb_path.is_file():
        raise SystemExit(f"setup.py: gdb path not found: {gdb_path}")
    if not launch_json.is_file():
        raise SystemExit(f"setup.py: launch.json not found: {launch_json}")

    update_symlink(vscode_dir, build_path)
    update_launch_json(
        launch_json=launch_json,
        toolchain_path=str(toolchain_path),
        gdb_path=str(gdb_path),
        device=args.device,
        toolchain_prefix=infer_toolchain_prefix(gdb_path),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())