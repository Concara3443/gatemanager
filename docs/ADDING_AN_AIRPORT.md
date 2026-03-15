# Adding a New Airport to Stand Manager

This guide explains how to add a new airport from scratch. It is written for both
human contributors and AI assistants. Follow every section in order - skipping
steps leads to silent failures at runtime.

---

## 1. Overview of the Data Model

Stand Manager is entirely data-driven. The application code contains **no
airport-specific logic**. Every airport is a folder under `airports/` containing
three JSON files:

```
airports/
+-- XXXX/               <- ICAO code, uppercase
    +-- config.json     <- airport metadata & dedicated airline map
    +-- airlines.json   <- airline to terminal (or dedicated config)
    +-- parkings.json   <- stand-by-stand data
```

Three global files in `data/` are shared by all airports and do **not** live
inside the airport folder:

```
data/
+-- aircraft_wingspans.json   <- wingspan in metres per ICAO type
+-- cargo_airlines.json       <- global list of cargo-only operators
+-- prefix_data.json          <- used for GA/private callsign detection
```

---

## 2. Gather Real-World Data First

Before writing a single line of JSON you need the following source material:

| What | Where to find it |
|---|---|
| Terminal/module layout | Airport AIP (AD 2 section), IVAO vACC charts |
| Stand numbers and their terminal | Airport PDC chart (Parking and Docking) |
| Maximum aircraft per stand | Same PDC chart - read the ICAO size category |
| Airline terminal assignments | AIP AD 2.18 or airline's published schedule at that airport |
| Dedicated stands per airline | Airport handling manual or AIP |
| GA/cargo apron location | PDC chart, look for stands marked "General Aviation" |

> **Tip for IVAO**: The vACC documentation often has a simplified stand chart
> that is faster to read than the official AIP. Use both to cross-reference.

---

## 3. `config.json` - Airport Metadata

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Full human-readable airport name |
| `terminals` | array of strings | yes | All terminal/module identifiers, in logical order |
| `dedicated_airline_map` | object | yes | Maps airline ICAO code to dedicated schengen category name |

### Rules

- `terminals` order matters: the GA fallback loop tries terminals in **reverse**
  order, so put the "main" terminal first.
- `dedicated_airline_map` can be an empty object `{}` if the airport has no
  dedicated stands.
- The category names in `dedicated_airline_map` are free-form strings - they
  just must match the `"schengen"` value used in `parkings.json` for those stands.

### Examples

**LEBL - Barcelona El Prat** (2 terminals, dedicated stands):
```json
{
  "name": "Barcelona El Prat",
  "terminals": ["T1", "T2"],
  "dedicated_airline_map": {
    "IBE": "ibe_dedicated",
    "EJU": "eju_ezy_ezs",
    "EZY": "eju_ezy_ezs",
    "EZS": "eju_ezy_ezs"
  }
}
```

**LEPA - Palma de Mallorca** (4 modules, no dedicated stands):
```json
{
  "name": "Palma de Mallorca",
  "terminals": ["A", "B", "C", "D"],
  "dedicated_airline_map": {}
}
```

**LEAL - Alicante-Elche** (single terminal):
```json
{
  "name": "Alicante-Elche",
  "terminals": ["T"],
  "dedicated_airline_map": {}
}
```

**LEMD - Madrid Barajas** (4 terminals, dedicated):
```json
{
  "name": "Madrid-Barajas",
  "terminals": ["T1", "T2", "T3", "T4"],
  "dedicated_airline_map": {
    "IBE": "iberia_dedicated",
    "IBS": "iberia_dedicated",
    "VLG": "vueling_dedicated"
  }
}
```

---

## 4. `airlines.json` - Airline Terminal Assignments

### Format

Each key is a 3-letter ICAO airline code. The value is one of three forms:

**Single terminal** - most common:
```json
"BAW": "T1"
```

**Multiple terminals** - airline operates from more than one terminal.
The app tries each one in order before falling back to others:
```json
"AFR": ["T1", "T2"]
```

**Object** - only needed when the airline has **dedicated stands**:
```json
"IBE": {
    "terminal": "T1",
    "dedicated": ["200", "202", "200R"],
    "label": "IBERIA DEDICATED"
}
```

The `terminal` field inside the object also accepts an array:
```json
"AFR": {
    "terminal": ["T1", "T2"],
    "dedicated": ["250", "252"],
    "label": "AIR FRANCE DEDICATED"
}
```

| Object field | Description |
|---|---|
| `terminal` | Home terminal(s) - string or array - used as fallback if dedicated stands are full |
| `dedicated` | Array of stand IDs from `parkings.json` |
| `label` | Text shown as the results header in the UI when dedicated stands are offered. Example: `"EASYJET DEDICATED"` appears as the title of the results group. |

### Special terminal values

| Value | Meaning |
|---|---|
| `"T1"`, `"T2"`, `"A"`, `"B"` ... | Any string matching a terminal in `config.json` |
| `["T1", "T2"]` | Airline uses both terminals - all are tried before falling back |
| `"CARGO"` | Airline operates cargo only - routed to cargo stands |

### Global cargo airlines — no entry needed

All airlines listed in `data/cargo_airlines.json` are **automatically assigned
`"CARGO"`** at load time for every airport. You do **not** need to add them to
an airport's `airlines.json`. Examples of auto-handled codes: `DHL`, `FDX`,
`UPS`, `CLX`, `GTI`, `GEC`, `TAY`, `BCS` (see the file for the full list).

If a cargo airline operates at your airport but is **not** in the global list,
add it to `data/cargo_airlines.json` instead of the per-airport file. Only use
an airport-level `"CARGO"` entry as an exception or override.

### Multi-terminal behaviour

When an airline has multiple terminals (`["T1", "T2"]`):
1. The app tries each assigned terminal in the order listed.
2. First terminal with available stands wins - no fallback label.
3. If **all** assigned terminals are full, it tries the remaining airport
   terminals (labelled as `fallback->Tx`).

When the controller manually overrides the terminal filter in the UI,
the override takes priority and only that terminal is searched.

### Example - LEPA (modules A-D)

```json
{
    "VLG": "A",
    "RYR": "B",
    "EJU": "B",
    "IBE": "A",
    "BAW": "A",
    "DLH": "A",
    "AFR": "A",
    "KLM": "A",
    "TAP": "A",
    "NAX": "C",
    "NOZ": "C",
    "EWG": "C",
    "TRA": "B",
    "WZZ": "D",
    "THY": "A",
    "RAM": "A"
}
```

> `DHL`, `FDX` and other cargo operators are handled automatically via
> `data/cargo_airlines.json` — no entry needed here.

### Example - LEAL (single terminal "T")

```json
{
    "VLG": "T",
    "RYR": "T",
    "EJU": "T",
    "EZY": "T",
    "IBE": "T",
    "BAW": "T",
    "TRA": "T",
    "WZZ": "T"
}
```

> **AI note**: When building `airlines.json`, if an airline is not listed and
> the user queries it, the app will ask the controller at runtime to enter the
> terminal manually - using the terminals defined in `config.json`. It is better
> to include all airlines that operate at the airport even if you are unsure.

---

## 5. `parkings.json` - Stand-by-Stand Data

This is the largest and most important file. Each key is a stand ID (string).

### Stand object fields

| Field | Type | Required | Description |
|---|---|---|---|
| `max_acft` | string | yes | ICAO type designator for the largest aircraft that fits the stand |
| `terminal` | string | yes | Terminal/module this stand belongs to (must match `config.json`) |
| `schengen` | string | yes | Stand category - see section 5.1 |
| `excludes` | array | yes | Stand IDs blocked when this stand is occupied (wing overlap) |
| `remote` | boolean | yes | `true` = remote stand (bus gate), `false` = contact gate (jetbridge) |

`max_wingspan` is **not required**. The app automatically looks it up from
`data/aircraft_wingspans.json` using `max_acft` at load time. Only add it
manually if the stand has a non-standard wingspan limit that differs from the
aircraft's published wingspan.

### 5.1 Schengen categories

The `schengen` field controls which flights can use a stand. Use exactly these
reserved values for standard categories:

| Value | When to use |
|---|---|
| `"schengen_only"` | Stand is inside the Schengen zone - non-Schengen flights cannot use it |
| `"non_schengen_only"` | Stand is outside - Schengen-only flights cannot use it |
| `"mixed"` | Stand can handle both Schengen and non-Schengen |
| `"ga"` | General Aviation apron - only assigned to GA/private traffic |
| `"cargo"` | Cargo apron - only assigned to cargo operators |
| `"maintenance"` | MRO/maintenance area - only used as GA fallback (last resort) |

**Custom dedicated categories** - for stands reserved for a specific airline or
group, use any string that is **not** one of the above. The string must also
appear as a value in `config.json`'s `dedicated_airline_map`. Example:

```
parkings.json  ->  "schengen": "eju_ezy_ezs"
config.json    ->  "EJU": "eju_ezy_ezs", "EZY": "eju_ezy_ezs"
```

Any value in `schengen` that is not a standard type and not in
`dedicated_airline_map` will cause those stands to be invisible to all airlines.
This can be used intentionally to mark stands as "out of service".

### 5.2 `max_acft` reference

Set `max_acft` to the ICAO type designator that matches the largest aircraft
the stand can physically accommodate, as published in the airport PDC chart.
The wingspan is resolved automatically. Some common types:

| ICAO type | Aircraft | Wingspan (m) |
|---|---|---|
| `C172` | Cessna 172 | 11.0 |
| `C208` | Cessna Caravan | 15.9 |
| `C560` | Citation V | 15.9 |
| `GLF4` | Gulfstream IV | 23.7 |
| `GLEX` | Global Express | 28.7 |
| `B735` | 737-500 | 28.9 |
| `A319` | Airbus A319 | 34.1 |
| `A320` | Airbus A320 | 35.8 |
| `A321` | Airbus A321 | 35.8 |
| `B738` | 737-800 | 35.8 |
| `B752` | 757-200 | 38.1 |
| `B763` | 767-300 | 47.6 |
| `A332` | A330-200 | 60.3 |
| `B788` | 787-8 | 60.1 |
| `A359` | A350-900 | 64.8 |
| `B744` | 747-400 | 64.4 |
| `A388` | A380-800 | 79.7 |

If `max_acft` is not in `data/aircraft_wingspans.json`, the stand will have no
wingspan limit (any aircraft fits). Add the type to the global database if needed.

### 5.3 `excludes` - Wing Overlap

When two adjacent stands cannot be occupied simultaneously because the aircraft
wings would overlap, they must list each other in `excludes`.

The exclusion is **bidirectional** - both stands must reference each other:

```json
"81": {
    "max_acft": "A321",
    "terminal": "T2",
    "schengen": "maintenance",
    "excludes": ["81A"],
    "remote": false
},
"81A": {
    "max_acft": "B744",
    "terminal": "T2",
    "schengen": "maintenance",
    "excludes": ["81", "82"],
    "remote": false
}
```

When stand `81A` is assigned, stands `81` and `82` are automatically blocked.
When stand `81` is assigned, stand `81A` is blocked.

> **AI note**: If you are unsure whether two stands have wing overlap, err on the
> side of caution and add the exclusion. A false exclusion is much less harmful
> than a wing-strike. When in doubt, check if the chart shows a note like
> "not simultaneous" or "dependent use".

### 5.4 Stand IDs

Stand IDs are strings and can be anything that appears on the real chart:
`"01"`, `"200"`, `"200R"`, `"A12"`, `"B4L"`, `"X1"`. Preserve leading zeros
as they appear on the chart - `"01"` and `"1"` are different stands.

### 5.5 Full example - LEPA Module A

```json
{
    "A01": {
        "max_acft": "A321",
        "terminal": "A",
        "schengen": "mixed",
        "excludes": ["A02"],
        "remote": false
    },
    "A02": {
        "max_acft": "A321",
        "terminal": "A",
        "schengen": "mixed",
        "excludes": ["A01", "A03"],
        "remote": false
    },
    "A03": {
        "max_acft": "A359",
        "terminal": "A",
        "schengen": "mixed",
        "excludes": ["A02"],
        "remote": false
    },
    "GA01": {
        "max_acft": "C208",
        "terminal": "A",
        "schengen": "ga",
        "excludes": [],
        "remote": false
    },
    "R01": {
        "max_acft": "B738",
        "terminal": "A",
        "schengen": "mixed",
        "excludes": [],
        "remote": true
    }
}
```

### 5.6 Full example - LEAL (single terminal "T")

```json
{
    "01": {
        "max_acft": "C172",
        "terminal": "T",
        "schengen": "ga",
        "excludes": [],
        "remote": false
    },
    "10": {
        "max_acft": "A321",
        "terminal": "T",
        "schengen": "schengen_only",
        "excludes": ["11"],
        "remote": false
    },
    "11": {
        "max_acft": "A321",
        "terminal": "T",
        "schengen": "schengen_only",
        "excludes": ["10", "12"],
        "remote": false
    },
    "12": {
        "max_acft": "A332",
        "terminal": "T",
        "schengen": "non_schengen_only",
        "excludes": ["11"],
        "remote": false
    },
    "30": {
        "max_acft": "B738",
        "terminal": "T",
        "schengen": "mixed",
        "excludes": [],
        "remote": true
    },
    "141": {
        "max_acft": "B744",
        "terminal": "T",
        "schengen": "cargo",
        "excludes": [],
        "remote": false
    }
}
```

---

## 6. Dedicated Stands - The Three-File Link

Dedicated stands require consistent data in **all three files**. Here is a
complete worked example for a hypothetical `VLG` (Vueling) dedicated setup at
a new airport `LEGE`:

### Step 1 - Choose a category name
Pick a short, lowercase, underscore-separated string. It must be unique within
this airport. For example: `"vlg_dedicated"`.

### Step 2 - `config.json`
```json
{
    "name": "Girona-Costa Brava",
    "terminals": ["T"],
    "dedicated_airline_map": {
        "VLG": "vlg_dedicated"
    }
}
```

### Step 3 - `airlines.json`
```json
{
    "VLG": {
        "terminal": "T",
        "dedicated": ["10", "11", "12"],
        "label": "VUELING DEDICATED"
    },
    "RYR": "T",
    "EJU": "T"
}
```

### Step 4 - `parkings.json`
```json
{
    "10": {
        "max_acft": "A321",
        "terminal": "T",
        "schengen": "vlg_dedicated",
        "excludes": ["11"],
        "remote": false
    },
    "11": {
        "max_acft": "A321",
        "terminal": "T",
        "schengen": "vlg_dedicated",
        "excludes": ["10", "12"],
        "remote": false
    },
    "12": {
        "max_acft": "A320",
        "terminal": "T",
        "schengen": "vlg_dedicated",
        "excludes": ["11"],
        "remote": false
    }
}
```

### How it works at runtime
1. User queries `VLG A320 LEPA` (Schengen).
2. `airlines.json` has `VLG` as dedicated - app looks up stands `["10","11","12"]`.
3. Those stands have `"schengen": "vlg_dedicated"`.
4. `config.json` maps `"VLG" -> "vlg_dedicated"` - VLG is allowed.
5. If all three stands are occupied, app falls back to standard `filter_parkings`
   on terminal `"T"` - which correctly **excludes** stands 10/11/12 for any
   airline that is not `VLG` (because `vlg_dedicated` is not in their
   `dedicated_map` entry).

---

## 7. How the `.spec` File Works (for EXE builds)

If you build a standalone `.exe` with PyInstaller, every JSON file must be
declared in `lebl_parking.spec` inside the `datas` list. Add your airport:

```python
datas=[
    ('data/aircraft_wingspans.json',   'data'),
    ('data/cargo_airlines.json',       'data'),
    ('data/prefix_data.json',          'data'),
    ('airports/LEBL/config.json',      'airports/LEBL'),
    ('airports/LEBL/airlines.json',    'airports/LEBL'),
    ('airports/LEBL/parkings.json',    'airports/LEBL'),
    # New airport:
    ('airports/LEAL/config.json',      'airports/LEAL'),
    ('airports/LEAL/airlines.json',    'airports/LEAL'),
    ('airports/LEAL/parkings.json',    'airports/LEAL'),
    ('assets/splash.png',              'assets'),
],
```

Omitting any file here will cause a crash when running the compiled `.exe`.
Running directly with Python (`python main.py`) does not require `.spec` changes.

---

## 8. Checklist Before Testing

Go through this list before launching the app:

- [ ] Folder name is the ICAO code in uppercase (`LEAL`, not `leal` or `Leal`)
- [ ] All three JSON files exist: `config.json`, `airlines.json`, `parkings.json`
- [ ] `config.json` - `terminals` is a non-empty array
- [ ] `config.json` - `dedicated_airline_map` exists (even if `{}`)
- [ ] `airlines.json` - every airline with dedicated stands has the object format
      with `"terminal"`, `"dedicated"` and `"label"` keys
- [ ] `airlines.json` - dedicated stand IDs in `"dedicated"` arrays exist as
      keys in `parkings.json`
- [ ] `airlines.json` - cargo airlines already in `data/cargo_airlines.json` are
      **not** duplicated here (the global list is auto-injected at load time)
- [ ] `parkings.json` - every stand's `"terminal"` value appears in
      `config.json`'s `terminals` array
- [ ] `parkings.json` - all IDs in `"excludes"` arrays exist as keys in the
      same file
- [ ] `parkings.json` - `"schengen"` values for dedicated stands match the
      values in `config.json`'s `dedicated_airline_map`
- [ ] `parkings.json` - every `max_acft` type exists in `data/aircraft_wingspans.json`,
      or the stand intentionally has no wingspan limit
- [ ] Exclusions are bidirectional: if `"A"` excludes `"B"`, then `"B"` must
      exclude `"A"` (unless the relationship is intentionally one-way)
- [ ] If building an EXE: `.spec` has been updated with the new airport files

---

## 9. Common Mistakes

### Wrong: terminal in `parkings.json` not in `config.json`
```json
// config.json
"terminals": ["T1", "T2"]

// parkings.json - BUG: "T3" is not declared
"200": { "terminal": "T3", ... }
```
Result: stand 200 will never appear in any query.

### Wrong: category name mismatch between config and parkings
```json
// config.json
"dedicated_airline_map": { "EJU": "easyjet_stands" }

// parkings.json - BUG: wrong category name
"91": { "schengen": "eju_dedicated", ... }
```
Result: stand 91 has a non-standard schengen type not in `dedicated_airline_map`,
so it will be excluded for ALL airlines including EJU.

### Wrong: dedicated stand not in `airlines.json`
```json
// airlines.json
"EJU": "T2"    <- simple string, no "dedicated" key

// parkings.json
"91": { "schengen": "eju_dedicated" }
```
Result: EJU will not be offered its dedicated stands first. It will get filtered
into the general T2 pool, and stands 91-96 will be blocked for everyone since
`eju_dedicated` is not in `dedicated_airline_map` (if config has no entry for it).

### Wrong: one-sided exclusion
```json
// Stand 200 excludes 202, but 202 does not exclude 200
"200": { "excludes": ["202"] },
"202": { "excludes": [] }
```
Result: assigning stand 202 will NOT block 200, allowing two simultaneous
conflicting assignments.

### Wrong: `max_acft` not in wingspans database
```json
"10": { "max_acft": "B78X", ... }
```
Result: stand will have no wingspan limit and will appear suitable for any
aircraft. Add `"B78X"` to `data/aircraft_wingspans.json` if needed.

---

## 10. Quick Reference - File Skeleton

Use these templates as starting points.

### `config.json`
```json
{
    "name": "Airport Full Name",
    "terminals": ["T1"],
    "dedicated_airline_map": {}
}
```

### `airlines.json`
```json
{
    "XXX": "T1",
    "YYY": "T1"
}
```

> Cargo airlines are injected automatically from `data/cargo_airlines.json`.
> Only add a `"CARGO"` entry here for an airline that is NOT in that global list.

### `parkings.json`
```json
{
    "01": {
        "max_acft": "A321",
        "terminal": "T1",
        "schengen": "mixed",
        "excludes": [],
        "remote": false
    }
}
```
