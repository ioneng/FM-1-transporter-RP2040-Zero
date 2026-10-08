# First-generation Raspberry Pi Pico W adaptation

This source snapshot is from `kurogedelic/FM-1-transporter` commit
`a632d923203170e3a08565f4056dbb3fd3d65ca5`. Its Pico-PIO-USB dependency is
included at commit `fe9133fc513b82cc3dc62c67cb51f2339cf29ef7`.
This is a source download, without Git history.

## Change

When built for `pico_w`, `src/recovery.c` disables the XIAO status LED
initialization and writes. XIAO's GPIO25 LED connection is Pico W's wireless
chip select. The existing USB console supplies status without enabling Wi-Fi.
XIAO builds retain their existing LED behavior. Recovery timing, GP0 and GP1,
and flash write safeguards are unchanged.

## Wiring

Use the first-generation RP2040 Pico W, not Pico 2 W.

| Pico W signal | FM-1 USB signal |
| --- | --- |
| GP0 | D+ |
| GP1 | D- |
| GND | GND |

Power the Pico W from the PC through its Micro USB connector. The FM-1 uses
its own battery. Do not connect the FM-1's VBUS to the Pico W. The XIAO names
`D6` and `D7` in upstream console messages mean GP0 and GP1, respectively.

## Build

From the FM-1 project directory, using the downloaded SDK, loader, and
picotool 2.2.0 source:

```bash
cmake -S dependencies/picotool -B dependencies/picotool-build \
  -DPICO_SDK_PATH="$PWD/pico-sdk" -DPICOTOOL_NO_LIBUSB=1 \
  -DPICOTOOL_FLAT_INSTALL=1 \
  -DCMAKE_INSTALL_PREFIX="$PWD/dependencies/picotool-install"
cmake --build dependencies/picotool-build --parallel 4
cmake --install dependencies/picotool-build
cmake -S FM-1-transporter -B FM-1-transporter/build-pico-w \
  -DPICO_BOARD=pico_w -DPICO_SDK_PATH="$PWD/pico-sdk" \
  -DFM1T_LOADER_BIN="$PWD/dependencies/wl82loader.bin" \
  -DPICO_NO_PICOTOOL=0 \
  -Dpicotool_DIR="$PWD/dependencies/picotool-install/picotool"
cmake --build FM-1-transporter/build-pico-w --parallel 4
```

Picotool is installed only inside this project. It has file conversion and
inspection support, but USB device access is disabled. The SDK now generates
the UF2 directly. Its output is byte-identical to the earlier conversion with
Microsoft's standard UF2 converter.

Do not run `git submodule update` in this snapshot: the dependency's files
are already included. The recovery build is
`build-pico-w/fm1_transporter.uf2`. The `fm1_transporter_hostonly.uf2`
build skips recovery entry and is for host diagnostics.

## Verification and limits

Build verified on 2026-10-07 with SDK 2.2.0 and ARM GCC 16.2.0.
Both targets compiled successfully with the loader embedded. The captured
configure and build logs contained no `warning:` or `error:` matches.
Both UF2 files passed checks for block headers, RP2040 family ID,
sequential flash addresses starting at `0x10000000`, and exact binary
payload reconstruction. Both binaries contain exactly one complete loader.
Picotool 2.2.0 also identifies the recovery UF2 as `rp2040`, board `pico_w`,
SDK 2.2.0, with binary start `0x10000000` and end `0x10018c68`.

Loader: 24064 bytes, Git blob SHA-1
`3b47cffaf7bd87f27163ca7bf0c7deb0c783ac87`.
Recovery UF2 SHA-256:
`eefee68ac11918dce4a647f8e088a112f66b690a59361ec031522321a55ca4e2`.
Host-only UF2 SHA-256:
`2e73ee25d1d950f78f81bde181d0de5a5577f1e904c80299b85082cc70a18f91`.

This adaptation has not been tested on a physical Pico W or FM-1. Before
writing any FM-1 firmware, verify recovery entry, chip identity, and two
matching full flash backups.

The local Python writing client now supports only the exact verified stock
V15 package without research-lab modules. See `RP2040-ZERO.md` for offline
verification and current hardware recovery status. Pico W hardware remains
untested; no cable-handover procedure for `jl-uboot-tool` is established.

## Sources

- [Pico SDK 2.2.0 Pico W board definition](https://github.com/raspberrypi/pico-sdk/blob/2.2.0/src/boards/include/boards/pico_w.h): board macro and wireless chip select on GPIO25.
- [Raspberry Pi board documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html): Pico W hardware and pinout.
- [Transporter source](https://github.com/kurogedelic/FM-1-transporter): original build, recovery, and wiring instructions.
