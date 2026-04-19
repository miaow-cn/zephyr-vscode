# VSCode Auto Setup

## Overview

This directory contains a post-build automation flow for Zephyr multi-app development.

After each successful build, `.vscode/setup.py` is executed to:

1. Update `.vscode/build` to point to the current app build directory.
2. Update Cortex-Debug fields in `.vscode/launch.json`:
	 - `executable`
	 - `armToolchainPath`
	 - `gdbPath`
	 - `toolchainPrefix`
	 - `device` (J-Link format, including loader when available)

This lets you switch between apps without manually editing debug settings.

## How It Works

1. The app `CMakeLists.txt` defines a custom command that depends on `zephyr/zephyr.elf`.
2. Once final linking is complete, CMake calls `.vscode/setup.py`.
3. `setup.py` validates inputs, updates the build symlink, and rewrites Cortex-Debug fields in `launch.json`.

## J-Link Device Format

The `device` value follows J-Link syntax:

- No loader: `<DEVICE>`
- With loader: `<DEVICE>?<LOADER_ARGS>`

Example:

```text
STM32H743XI?BankAddr=0x90000000&Loader=CLK@PF10_nCS@PG6_D0@PF8_D1@PF9_D2@PF7_D3@PF6
```

This value is assembled in CMake from `BOARD_RUNNER_ARGS_jlink`.

## Minimal CMake Example

Use the snippet below in an app `CMakeLists.txt` to integrate post-link setup.

```cmake
find_package(Python3 REQUIRED COMPONENTS Interpreter)

set(VSCODE_SETUP_SCRIPT ${ZEPHYR_BASE}/../.vscode/setup.py)
if(EXISTS ${VSCODE_SETUP_SCRIPT})
	get_filename_component(VSCODE_ARM_TOOLCHAIN_PATH ${CMAKE_GDB} DIRECTORY)

	set(VSCODE_JLINK_DEVICE "")
	set(VSCODE_JLINK_LOADER "")
	get_property(VSCODE_JLINK_ARGS GLOBAL PROPERTY BOARD_RUNNER_ARGS_jlink)

	foreach(arg IN LISTS VSCODE_JLINK_ARGS)
		if(arg MATCHES "^--device=(.*)$")
			set(VSCODE_JLINK_DEVICE ${CMAKE_MATCH_1})
		elseif(arg MATCHES "^--loader=(.*)$")
			set(VSCODE_JLINK_LOADER ${CMAKE_MATCH_1})
		endif()
	endforeach()

	if(VSCODE_JLINK_LOADER)
		set(VSCODE_JLINK_DEVICE_FULL "${VSCODE_JLINK_DEVICE}?${VSCODE_JLINK_LOADER}")
	else()
		set(VSCODE_JLINK_DEVICE_FULL ${VSCODE_JLINK_DEVICE})
	endif()

	set(VSCODE_SETUP_STAMP ${CMAKE_BINARY_DIR}/.vscode_setup.stamp)
	add_custom_command(
		OUTPUT ${VSCODE_SETUP_STAMP}
		COMMAND ${Python3_EXECUTABLE} ${VSCODE_SETUP_SCRIPT}
			--app-path ${CMAKE_CURRENT_SOURCE_DIR}
			--build-path ${CMAKE_BINARY_DIR}
			--toolchain-path ${VSCODE_ARM_TOOLCHAIN_PATH}
			--gdb-path ${CMAKE_GDB}
			--device ${VSCODE_JLINK_DEVICE_FULL}
			--launch-json ${ZEPHYR_BASE}/../.vscode/launch.json
		COMMAND ${CMAKE_COMMAND} -E touch ${VSCODE_SETUP_STAMP}
		DEPENDS ${CMAKE_BINARY_DIR}/zephyr/zephyr.elf ${VSCODE_SETUP_SCRIPT}
		COMMENT "Run .vscode/setup.py to update launch.json and build symlink"
		VERBATIM
	)
	add_custom_target(vscode_setup_symlink ALL DEPENDS ${VSCODE_SETUP_STAMP})
endif()
```

## Daily Usage

1. Build any app, for example:

```bash
west build -d app/98-cpp/build app/98-cpp -b fk743m5_xih6
```

2. After build, `setup.py` updates `.vscode/build` and `.vscode/launch.json`.
3. Start debugging in VS Code using `Launch` or `Attach`.

## Troubleshooting

### setup.py did not run

1. Confirm `.vscode/setup.py` exists.
2. Confirm the app `CMakeLists.txt` includes the post-link custom command.
3. Confirm `zephyr/zephyr.elf` was generated.

### Wrong GDB path

`gdbPath` is derived from `CMAKE_GDB`. Verify your Zephyr toolchain setup and cache values.

### Device string missing loader

Check that the app sets J-Link runner args with:

- `--device=...`
- Optional `--loader=...`

## Git Ignore Suggestion

Keep `.vscode/build` ignored in `.vscode/.gitignore`:

```text
build
```

