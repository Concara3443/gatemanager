"""
Validador de datos de aeropuerto.

Uso:
    python dev/validate_airport.py          # valida todos los aeropuertos
    python dev/validate_airport.py LEBL     # valida solo LEBL
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AIRPORTS_DIR = os.path.join(ROOT, "airports")
WINGSPANS_PATH = os.path.join(ROOT, "data", "aircraft_wingspans.json")

VALID_SCHENGEN = {"schengen_only", "non_schengen_only", "mixed", "ga", "cargo", "maintenance"}

# ── helpers ──────────────────────────────────────────────────────────────────

OK = "\033[92m[OK]\033[0m"
WR = "\033[93m[!] \033[0m"
ER = "\033[91m[X]\033[0m"


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


class Report:
    def __init__(self, icao):
        self.icao = icao
        self.errors = []
        self.warnings = []

    def err(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def print(self):
        status = ER if self.errors else (WR if self.warnings else OK)
        print(f"\n{status}  {self.icao}")
        for m in self.errors:
            print(f"    {ER} {m}")
        for m in self.warnings:
            print(f"    {WR} {m}")
        if not self.errors and not self.warnings:
            print(f"    {OK} Sin problemas")
        return len(self.errors), len(self.warnings)


# ── validators ────────────────────────────────────────────────────────────────


def validate(icao, wingspans):
    r = Report(icao)
    base = os.path.join(AIRPORTS_DIR, icao)

    # --- load files ---
    for fname in ("config.json", "airlines.json", "parkings.json"):
        if not os.path.exists(os.path.join(base, fname)):
            r.err(f"Falta el archivo {fname}")
    if r.errors:
        return r

    config = _load(os.path.join(base, "config.json"))
    airlines = _load(os.path.join(base, "airlines.json"))
    parkings = _load(os.path.join(base, "parkings.json"))

    terminals = config.get("terminals", [])
    dedicated_map = config.get("dedicated_airline_map", {})
    stand_ids = set(parkings.keys())

    # --- config ---
    if not config.get("name"):
        r.err("config.json: falta el campo 'name'")
    if not terminals:
        r.err("config.json: 'terminals' está vacío o no existe")

    # --- dedicated_airline_map cross-check ---
    for airline, cat in dedicated_map.items():
        if airline not in airlines:
            r.warn(f"config.json dedicated_airline_map: '{airline}' no está en airlines.json")
        val = airlines.get(airline)
        if isinstance(val, dict) and val.get("dedicated"):
            for stand in val["dedicated"]:
                if stand not in stand_ids:
                    r.err(
                        f"airlines.json [{airline}] dedicated: stand '{stand}' no existe en parkings.json"
                    )

    # --- airlines ---
    for code, val in airlines.items():
        if isinstance(val, str):
            term = val
        elif isinstance(val, list):
            for t in val:
                if t not in terminals and t != "CARGO":
                    r.warn(f"airlines.json [{code}]: terminal '{t}' no definida en config.json")
            continue
        elif isinstance(val, dict):
            term = val.get("terminal", "")
            if not val.get("dedicated"):
                r.warn(f"airlines.json [{code}]: objeto sin campo 'dedicated'")
        else:
            r.err(f"airlines.json [{code}]: valor inesperado ({type(val).__name__})")
            continue

        if term and term not in terminals and term != "CARGO":
            r.warn(f"airlines.json [{code}]: terminal '{term}' no definida en config.json")

    # --- parkings ---
    for pid, data in parkings.items():
        prefix = f"parkings.json [{pid}]"

        # terminal
        term = data.get("terminal")
        if not term:
            r.err(f"{prefix}: falta 'terminal'")
        elif term not in terminals and term != "CARGO":
            r.warn(f"{prefix}: terminal '{term}' no definida en config.json")

        # schengen
        stype = data.get("schengen")
        if not stype:
            r.warn(f"{prefix}: falta 'schengen'")
        elif stype not in VALID_SCHENGEN and stype not in {v for v in dedicated_map.values()}:
            r.warn(f"{prefix}: valor de schengen desconocido '{stype}'")

        # wingspan / max_acft
        if "max_wingspan" not in data and "max_acft" not in data:
            r.err(f"{prefix}: falta 'max_wingspan' y 'max_acft'")
        elif "max_acft" in data and data["max_acft"] not in wingspans:
            r.warn(f"{prefix}: max_acft '{data['max_acft']}' no está en aircraft_wingspans.json")

        # excludes exist
        for ex in data.get("excludes", []):
            if ex not in stand_ids:
                r.err(f"{prefix}: exclude '{ex}' no existe en parkings.json")

        # remote field
        if "remote" not in data:
            r.warn(f"{prefix}: falta 'remote'")

    # --- excludes symmetry ---
    for pid, data in parkings.items():
        for ex in data.get("excludes", []):
            if ex in parkings:
                reverse = parkings[ex].get("excludes", [])
                if pid not in reverse:
                    r.warn(
                        f"parkings.json: excludes no simétrico — [{pid}] excluye '{ex}' pero '{ex}' no excluye '{pid}'"
                    )

    return r


# ── main ──────────────────────────────────────────────────────────────────────


def main():
    if not os.path.isdir(AIRPORTS_DIR):
        print(f"{ER} No se encontró la carpeta airports/ en {ROOT}")
        sys.exit(1)

    target = sys.argv[1].upper() if len(sys.argv) > 1 else None
    airports = (
        [target]
        if target
        else [d for d in os.listdir(AIRPORTS_DIR) if os.path.isdir(os.path.join(AIRPORTS_DIR, d))]
    )

    if not airports:
        print(f"{ER} No hay aeropuertos en {AIRPORTS_DIR}")
        sys.exit(1)

    if not os.path.exists(WINGSPANS_PATH):
        print(f"{ER} No se encontró data/aircraft_wingspans.json")
        sys.exit(1)

    wingspans = _load(WINGSPANS_PATH)

    total_err = total_warn = 0
    for icao in sorted(airports):
        path = os.path.join(AIRPORTS_DIR, icao)
        if not os.path.isdir(path):
            print(f"{ER} Aeropuerto '{icao}' no encontrado en {AIRPORTS_DIR}")
            continue
        rep = validate(icao, wingspans)
        e, w = rep.print()
        total_err += e
        total_warn += w

    print(f"\n{'-' * 40}")
    if total_err == 0 and total_warn == 0:
        print(f"{OK}  Todo correcto")
    else:
        print(f"  {ER} {total_err} error(s)   {WR} {total_warn} aviso(s)")

    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
