# Change log

Hardware revisions, newest first. Each release is tagged `rev-<letter>`.

## Rev B — 2026-11-05

Power board PCB. The sensor board is unchanged and stays at Rev A.

### Power board

- PCB laid out: 110 × 30 mm with the outline and M3 holes of the sensor board, one copper layer for toner
  transfer, the same track and gap rules, ground fill with thermal reliefs.
- Two wire links on the component side: W1 carries +3V3 over the I2C tracks, W2 carries ground to the 5 V boost.
  A 1.0 mm ground track runs under D2, which uses a footprint with 2.4 mm between its pads.
- 3.3 V now from an RT9080-33 LDO (U5) through a MAX40200 ideal diode (U3), instead of the TPS63020 module and the
  LM66100.
- Sensor 5 V now from an MT3608 boost converter on the board (U6, L1, D3, set to 5.0 V by R4 and R5), still
  switched by the TPS2051B (U4).
- The INA226 modules (U1, U2) stand upright in 8 way sockets; the CN3791 module (M1) plugs into a 4 way socket.
- The battery is a 1S pack with its own BMS on a JST XH side entry header; the BMS module and the BAT_ISO jumper
  are removed. R7 (0 Ω) is the battery link and can be removed for a current measurement.
- The I2C expansion header J3 is removed. J2 is now a 3.5 mm screw terminal and J1 a JST XH side entry header.
- Module envelope drawing: 134 × 30 × 43.6 mm with the mated plugs, round tube of at least 53 mm inner diameter.

### Library

- New footprints: INA226 socket (upright), CN3791 socket, JST XH 2 way side entry, SOT-23-5 and SOT-23-6 on the
  copper side, SMA with a wide gap, radial 6.3 mm capacitor, radial 8 mm inductor, 2 mm test pad.
- New symbols: MAX40200, MT3608, RT9080-33. Removed: LM66100, BMS and DC-DC module symbols.

### Tools

- `tools/make_outputs.py` makes the copper artwork, assembly drawing and figures for both boards, and the module
  envelope of the power board.

### Documents

- VNT-002 Vantage — Power board — Fabrication, assembly and test, second edition (was Description and test).
- VNT-001: reference to VNT-002 updated to its new title; no technical change.

## Rev A — 2026-10-25

First release in this repository. It consolidates the earlier, unreleased design iterations.

### Sensor board

- ESP32-S3 dev board carrier, 110 × 30 mm, single copper layer for toner transfer.
- Tracks 0.6 mm (signals) and 1.0 mm (supplies, ground), gaps 0.5 mm, 0.8 mm from the edge; ground fill with
  thermal reliefs and none under the dev board antenna.
- Two wire links (L1, L2) on the component side complete the ground.
- Interfaces: J1 power board (JST XH 6-way side entry), J2 AJ-SR04M, J3 BME280, J4 rain gauge, J5 TF-Luna.
- JP1 (3V3 FEED) and JP2 (BENCH 5V) select field mode or bench mode.
- Protection: TVS and RC filter on the rain input, series resistors on the sensor lines, PTC on the TF-Luna
  supply, BME280 supplied from a GPIO through 100 Ω, 5 V echo divided to about 3.2 V.

### Power board

- Schematic only; the PCB layout is not started.
- 18650 cell with 1S protection module, 1.5 A PTC and BAT_ISO jumper.
- Solar input with TVS and Schottky protection, CN3791 MPPT charger.
- INA226 current monitors for the solar input (0x40) and the battery (0x44).
- 3.3 V from a TPS63020 buck-boost module through an LM66100 ideal diode.
- Sensor 5 V from a boost module switched by a TPS2051B (SENS_EN, 10 kΩ pull-down).

### Documents

- VNT-001 Vantage — Sensor board — Fabrication, assembly and test, first edition.
- VNT-002 Vantage — Power board — Description and test, first edition.
