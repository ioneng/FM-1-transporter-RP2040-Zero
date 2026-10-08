# Waveshare RP2040-Zero, RP2040

Status on 2026-10-08: build verified; standalone hardware USB gate passed
using user-reported terminal results. FM-1 recovery and backups remain untested.

## Board changes

The SDK 2.2.0 board definition uses a WS2812 on GP16, not the XIAO's
three GPIO LEDs. `src/recovery.c` disables XIAO LED initialization and
writes for `WAVESHARE_RP2040_ZERO`, retaining the existing Pico W branch.
`src/main.c` prints the Zero's GP0/GP1 names in its startup banner.
No WS2812 driver or extra PIO state machine was added.

GP0 and GP1 remain the recovery and software-host pins. Default UART
pin definitions do not activate UART output: the build disables it.
Recovery remains on PIO0, host on PIO1, and PC USB on the native controller.
The onboard RGB LED is not used as a firmware-health indicator.

## Build

Run from the outer FM-1 project directory:

```bash
cmake -S FM-1-transporter -B FM-1-transporter/build-rp2040-zero \
  -DPICO_BOARD=waveshare_rp2040_zero \
  -DPICO_SDK_PATH="$PWD/pico-sdk" \
  -DFM1T_LOADER_BIN="$PWD/dependencies/wl82loader.bin" \
  -DPICO_NO_PICOTOOL=0 \
  -Dpicotool_DIR="$PWD/dependencies/picotool-install/picotool" \
  -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build FM-1-transporter/build-rp2040-zero --parallel 4
```

Both commands passed. Captured configure and final build logs have no
`warning:` or `error:` matches. Both firmware targets built successfully.

Use `build-rp2040-zero/fm1_transporter.uf2` for recovery.
The host-only UF2 skips the recovery key and is not the initial test image.

Recovery UF2 SHA-256:
`88746f9185c8d65e1cbbad6efe8652453a2c4b5e59e3805356e4e36efd045fab`.

Host-only UF2 SHA-256:
`1da8ac7ff221757d21b22c6fcff4e0322cfeb34993e04be2d2a89780008ec0c5`.

## Build proof

- Picotool reports RP2040 family, `waveshare_rp2040_zero`, SDK 2.2.0,
  and `boot2_w25q080`. Recovery binary occupies [0x10000000, 0x10018c78).
- Actual compiler preprocessing of Zero recovery code shows no XIAO LED
  GPIO accesses and retains GP0/GP1 initialization.
- Both UF2s pass header, family ID, sequential address, and exact binary
  payload reconstruction checks.
- Both binaries contain exactly one complete 24064-byte loader matching
  upstream Git blob SHA-1 `3b47cffaf7bd87f27163ca7bf0c7deb0c783ac87`.

## Standalone hardware gate

1. Identify the connected Zero's RPI-RP2 mount path and copy the recovery
   UF2 onto it. Leave all GPIOs and the FM-1 disconnected.
2. Verify native USB enumeration as `2e8a:000a`, product FM-1 Transporter,
   with two CDC ports (console interface 0 and data interface 2).
3. Open the console at 115200 baud and capture the Zero startup banner and
   recovery logs. With no target, waiting for recovery is expected.
4. Send `ping\n` to the data port and require `PONG`.

User-reported results on 2026-10-08:

- Flashed the Zero recovery UF2 through RPI-RP2.
- USB enumerated as `2e8a:000a`, `kurogedelic FM-1 Transporter`.
- Serial ID `4250304D30363707`, console if00 mapped to ttyACM0 and data
  if02 mapped to ttyACM1.
- Data `ping` returned `b'PONG\n'`.
- Console returned repeated `KEY` packet counts increasing by 4090 at
  approximately two-second intervals, confirming the recovery loop runs.
  The startup banner was not captured. Physical GP0/GP1 waveforms and
  target recovery acknowledgement have not been measured.
- Normal-user serial access returned PermissionError; the user ran the
  bounded serial tests with sudo successfully.

These are user-performed checks, not direct agent hardware verification.
The agent environment cannot access USB or serial devices.

## Wiring preparation

With component side facing you and USB-C at the top, GP0 is the uppermost
right-edge hole, GP1 is immediately below it, and GND is the second
left-edge hole from the top, between 5V and 3V3. Confirm PCB labels.
Use GP0 to FM-1 USB D+, GP1 to D-, and GND to GND. Leave FM-1 USB VBUS
unconnected and insulated. Power the FM-1 from its battery and the Zero
through its own native USB-C port. Verify cable conductor identities
before connecting, rather than relying on wire colours.

## Recovery and restoration checkpoint, 2026-10-08

User reported UBOOT INQUIRY as WL82 UBOOT1.00 and chip information
`OK key=980F type=3 id=856014`. Both full backups in
`../fm1-backup-Iu3ELzCR/` are 1048576 bytes and identical, SHA-256
`8829a8d0d3becbfa9c13a2f50723f4a7d5d7c119b9a8fbc786d6da4394074ecf`.
The agent independently read and compared both local files. The protected
[0, 0x4000) region equals the inspected V15 image; all 143 application
sectors differ.

The local writing client now accepts only the exact inspected stock V15
package, SHA-256 pinned in `tools/fm1t.py`. After that check it extracts the
known flash entry at file offset 0x414, length 0x93000. It does not parse
arbitrary packages, accept custom firmware, or depend on research-lab
modules. Chip checks, fresh package-region comparison with the backup,
protected boot sectors, dry-run default, and final full read-back remain.
There are no new retries, background jobs, or privileged operations.

Verification command:

```bash
python -m unittest discover -s FM-1-transporter/tools -p test_fm1t.py -v
```

Final result: all nine offline tests passed without warnings. Initial test
execution failed because the test used `enter_context` instead of
`enterContext`; corrected. The next run exposed an existing unclosed
reference-file warning; `cmd_write` now closes that file using `with`.
A separate mocked dry run using the actual saved backup passed and planned
143 application sectors without accessing hardware or sending writes.

## Recovery outcome: complete, 2026-10-08

User performed the live dry run. It confirmed chip identity, 143 differing
application sectors, and a fresh full flash read matching the saved backup.
No device-data changes were reported. The dry run wrote nothing.

User then ran the same command with `--write` and reported:
`final full read EQUALS the expected image`.
This is the client's full-flash comparison, including preserved boot and
current device-data regions, not just the restored application.

After disconnecting the sacrificial FM-1 USB cable and power-cycling, the
user reported the original firmware interface displayed normally with a
low-battery warning. Recovery to stock V15 and the boot check succeeded.
These hardware outcomes are user-reported. Audio, MIDI, and saved settings
have not been functionally tested. Charge using an intact normal USB cable
before further use. Preserve both backups in `../fm1-backup-Iu3ELzCR/`.

Sources: SDK `src/boards/include/boards/waveshare_rp2040_zero.h`,
Transporter source, and [Waveshare board documentation](https://www.waveshare.com/wiki/RP2040-Zero).
