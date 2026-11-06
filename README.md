# Vantage

Design files and firmware of the **Vantage** IoT sensor node, by Team sevenUP. The node is the field unit of a
flood-monitoring system. This repository holds the hardware (schematics, PCB layout, libraries, drawings and the
instruction documents) and the node firmware.

**Current release: Rev B** (2026-11-05), tag `rev-B`: power board Rev B, sensor board Rev A (unchanged).

| Board | Status |
|---|---|
| Sensor board | Schematic and PCB complete. Single-sided, made at home by toner transfer. |
| Power board | Schematic and PCB complete. One copper layer, made at home by toner transfer, same outline and mounting holes as the sensor board. |

The node is two boards joined by one 6-way JST XH cable (J1 to J1):

- **Sensor board**: carries the ESP32-S3 dev board (YD-ESP32-S3, header rows 25.4 mm apart) and the sensor
  interfaces: AJ-SR04M ultrasonic, BME280, rain gauge, TF-Luna (optional).
- **Power board**: protected 1S battery pack, solar MPPT charger module, 3.3 V LDO with ideal diode, switched
  5 V boost for the sensors (SENS_EN) and two INA226 current monitor modules.

## Repository layout

```
Vantage-Hardware/
├── sensor-board/           KiCad project of the sensor board (schematic + PCB)
├── power-board/            KiCad project of the power board (schematic + PCB)
├── lib/                    shared Vantage symbol and footprint library
├── outputs/
│   ├── sensor-board/       schematic PDF, copper artwork, assembly drawing, BOM, drill table
│   └── power-board/        schematic PDF, copper artwork, assembly drawing, envelope, BOM, drill table
├── docs/                   instruction documents (PDF)
│   └── src/                document sources, figures, fonts and build script
├── firmware/               ESP32-S3 firmware (PlatformIO) and the gateway receiver
└── tools/                  script that regenerates the drawings in outputs/
```

## Files

### KiCad design files

| File | Description |
|---|---|
| `sensor-board/Vantage_Sensor.kicad_pro` | Sensor board project (design rules for toner transfer: 0.6 / 1.0 mm tracks, 0.5 mm gaps) |
| `sensor-board/Vantage_Sensor.kicad_sch` | Sensor board schematic |
| `sensor-board/Vantage_Sensor.kicad_pcb` | Sensor board PCB, 110 × 30 mm, copper on the bottom only, two wire links on top |
| `sensor-board/fp-lib-table`, `sym-lib-table` | Project library tables, pointing to `lib/` |
| `power-board/Vantage_Power.kicad_pro` | Power board project (same design rules for toner transfer as the sensor board) |
| `power-board/Vantage_Power.kicad_sch` | Power board schematic |
| `power-board/Vantage_Power.kicad_pcb` | Power board PCB, 110 × 30 mm, copper on the bottom only, two wire links on top |
| `power-board/Vantage_Power.kicad_dru` | Custom design rule: 0.35 mm clearance between the pins of the SOT-23 parts |
| `power-board/fp-lib-table`, `sym-lib-table` | Project library tables, pointing to `lib/` |

### Library

| File | Description |
|---|---|
| `lib/Vantage.kicad_sym` | Symbols: ESP32-S3 dev board, INA226 module, CN3791 module, MAX40200, MT3608, RT9080-33, TPS2051B |
| `lib/Vantage.pretty/` | Footprints with enlarged pads for toner transfer and hand drilling; SMD footprints placed on the copper side |

### Drawings and tables (`outputs/`)

| File | Description |
|---|---|
| `outputs/sensor-board/Vantage_Sensor_Schematic.pdf` | Sensor board schematic |
| `outputs/sensor-board/Vantage_Sensor_Copper-Artwork_Letter.pdf` | Copper artwork, 1:1, four copies on US Letter. **Print at 100 % / Actual size, do not mirror.** |
| `outputs/sensor-board/Vantage_Sensor_Copper-Artwork_A4.pdf` | Same, on A4 |
| `outputs/sensor-board/Vantage_Sensor_Assembly-Drawing.pdf` | Assembly drawing, 2:1: component side and copper side |
| `outputs/sensor-board/Vantage_Sensor_BOM.csv` | Sensor board bill of materials |
| `outputs/sensor-board/Vantage_Sensor_Drill.csv` | Drill sizes and counts |
| `outputs/power-board/Vantage_Power_Schematic.pdf` | Power board schematic |
| `outputs/power-board/Vantage_Power_Copper-Artwork_Letter.pdf` | Copper artwork, 1:1, four copies on US Letter. **Print at 100 % / Actual size, do not mirror.** |
| `outputs/power-board/Vantage_Power_Copper-Artwork_A4.pdf` | Same, on A4 |
| `outputs/power-board/Vantage_Power_Assembly-Drawing.pdf` | Assembly drawing, 2:1: component side and copper side |
| `outputs/power-board/Vantage_Power_Envelope.pdf` | Module envelope, 1:1: the space the assembled board needs in the enclosure |
| `outputs/power-board/Vantage_Power_BOM.csv` | Power board bill of materials |
| `outputs/power-board/Vantage_Power_Drill.csv` | Drill sizes and counts |

### Documents (`docs/`)

The documents follow the layout of ISO documents: cover, contents, foreword, introduction, numbered clauses
(scope, references, terms, ...), normative and informative annexes, bibliography.

| File | Description |
|---|---|
| `docs/VNT-001_Sensor-board_Fabrication-assembly-test.pdf` | **VNT-001** Vantage — Sensor board — Fabrication, assembly and test |
| `docs/VNT-002_Power-board_Fabrication-assembly-test.pdf` | **VNT-002** Vantage — Power board — Fabrication, assembly and test |
| `docs/src/VNT-001.md`, `VNT-002.md` | Document sources (edit these, then rebuild the PDFs) |
| `docs/src/build.py` | Builds the PDFs from the sources |
| `docs/src/iso.css` | Page layout and styles |
| `docs/src/figures/` | Figures used by the documents |
| `docs/src/fonts/` | Caladea font (SIL Open Font License, `OFL.txt`) |

### Firmware (`firmware/`)

| File | Description |
|---|---|
| `firmware/README.md` | Setup, build environments, power modes and the data format |
| `firmware/platformio.ini` | PlatformIO project: `field` (normal operation) and `bench` (bench and functional tests) |
| `firmware/include/config.h` | Node ID, gateway URL, mounting height, intervals and battery thresholds |
| `firmware/include/pins.h` | Pin map (VNT-001, Annex C) |
| `firmware/include/secrets.example.h` | Template for the Wi-Fi credentials; copy to `secrets.h`, which is not committed |
| `firmware/src/` | Firmware sources: sensors, rain gauge, power monitors, uplink, sleep and power modes |
| `firmware/tools/receiver.py` | Receiver for the gateway computer; writes the readings to a CSV file |

### Tools

| File | Description |
|---|---|
| `tools/make_outputs.py` | Regenerates the schematic PDFs, copper artwork, assembly drawings, power board envelope and document figures with `kicad-cli`; `python3 tools/make_outputs.py power` does one board |

## Opening the design

The KiCad files are in the KiCad 7 format; KiCad 8, 9 and 10 open them. The first save in KiCad 10 upgrades the
file format; commit that upgrade on its own, without other changes, so later diffs stay readable.

Both projects use the shared library in `lib/` through their own library tables, so no global library setup is
needed.

## Title blocks

Every file carries the same title block content: **Team sevenUP**, title **Vantage — Sensor board** or
**Vantage — Power board**, date and revision. No comment lines. The documents carry the same fields in the title
block on their cover.

## Revisions

All files of a release share one revision letter, shown in every title block and on the document covers. Each
release is tagged `rev-<letter>` and listed in [`CHANGELOG.md`](CHANGELOG.md). Things that need to change are
tracked as GitHub issues.

To make a new revision:

1. Change the design in KiCad.
2. Set the new revision letter and date in the title block of every changed file (Page Settings in KiCad).
3. Regenerate the drawings: `python3 tools/make_outputs.py`, or plot them from KiCad.
4. Update the BOM and drill CSV files if parts or holes changed.
5. Update the document sources (`edition`, `date`, `rev` and the content) and rebuild: `python3 docs/src/build.py`.
6. Add the revision to `CHANGELOG.md`, commit, and tag it `rev-<letter>`.

## Rebuilding the outputs

Drawings (needs KiCad's `kicad-cli` on the PATH, or its path in `KICAD_CLI`):

```
pip install pypdf reportlab
python3 tools/make_outputs.py
```

Documents:

```
pip install markdown beautifulsoup4 weasyprint
python3 docs/src/build.py
```
