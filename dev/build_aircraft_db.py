"""
build_aircraft_db.py
Scans OpenAircraftType-master/src/ and produces aircraft_wingspans.json
Only IFR aircraft: ENG_TYPE = J (jet) or T (turboprop)
"""
import os
import json
import configparser

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "OpenAircraftType-master", "src")
OUTPUT  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "aircraft_wingspans.json")

# Known wingspans (meters) — DB data takes priority, these fill gaps
AIRCRAFT_WINGSPANS = {
    # Airbus narrowbody
    "A318": 34.1, "A319": 35.8, "A320": 35.8, "A321": 35.8,
    "A19N": 35.8, "A20N": 35.8, "A21N": 35.8,  # neo family
    # Airbus widebody
    "A306": 44.8, "A30B": 44.8,
    "A310": 43.9,
    "A332": 60.3, "A333": 60.3, "A338": 60.3, "A339": 64.0,
    "A342": 60.3, "A343": 60.3, "A345": 63.45, "A346": 63.45,
    "A359": 64.75, "A35K": 64.75,
    "A388": 79.75,
    # Boeing narrowbody
    "B712": 28.4,
    "B721": 32.9, "B722": 32.9,
    "B731": 28.3, "B732": 28.9, "B733": 28.9, "B734": 28.9, "B735": 28.9,
    "B736": 34.3, "B737": 34.3, "B738": 35.8, "B739": 35.8,
    "B37M": 35.9, "B38M": 35.9, "B39M": 35.9,  # MAX family
    "B752": 38.1, "B753": 38.1,
    # Boeing widebody
    "B762": 47.6, "B763": 47.6, "B764": 51.9,
    "B772": 60.9, "B773": 64.8, "B77L": 64.8, "B77W": 64.8,
    "B778": 71.8, "B779": 71.8,  # 777X
    "B788": 60.1, "B789": 60.1, "B78X": 60.1,
    "B744": 64.4, "B748": 68.4,
    # Embraer
    "E170": 26.0, "E175": 26.0,
    "E190": 28.7, "E195": 28.7,
    "E75L": 26.0, "E75S": 26.0,
    "E290": 31.0, "E295": 31.0,  # E2 family
    # Bombardier / CRJ
    "CRJ1": 21.2, "CRJ2": 21.2,
    "CRJ7": 23.2, "CRJ9": 24.9, "CRJX": 24.9,
    # Bombardier / Dash 8 
    "DH8A": 25.9, "DH8B": 25.9, "DH8C": 27.4, "DH8D": 28.4,
    # ATR
    "AT43": 24.6, "AT45": 24.6, "AT46": 24.6,
    "AT72": 27.1, "AT73": 27.1, "AT75": 27.1, "AT76": 27.1,
    # Airbus A220 (ex Bombardier C Series) 
    "BCS1": 35.1, "BCS3": 35.1, "CS1": 35.1, "CS3": 35.1,
    "A220": 35.1, "A21N": 35.8,
    # McDonnell Douglas
    "DC85": 43.4, "DC86": 43.4, "DC87": 43.4, "DC9": 28.5,
    "MD11": 51.7, "MD81": 32.8, "MD82": 32.8, "MD83": 32.8, "MD88": 32.8, "MD90": 32.9,
    # COMAC
    "C919": 35.8, "ARJ21": 27.3,
    # Sukhoi / Irkut
    "SU95": 27.8,
    # Fokker
    "F50":  29.0, "F70":  28.1, "F100": 28.1,
    # Business jets
    "C510": 13.16, "C525": 14.4, "C560": 15.9, "C56X": 15.9,
    "C680": 22.04, "C68A": 22.04, "C750": 21.09,
    "CL30": 19.5, "CL35": 19.5, "CL60": 19.6,
    "GL5T": 28.7, "GLEX": 28.7, "G280": 28.6, "G150": 16.9,
    "GLF4": 23.7, "GLF5": 28.5, "GLF6": 30.4,
    "F2TH": 21.4, "F900": 19.3, "F7X":  26.2,
    "E35L": 18.0, "E50P": 11.7, "E55P": 14.2,
    "LJ35": 13.4, "LJ45": 14.6, "LJ60": 14.6, "LJ75": 14.6,
    "B350": 17.7, "BE40": 13.3, "PC12": 16.3, "PC24": 17.4,
    # Helicopters
    "S76":  13.4, "EC25": 16.2, "EC35": 12.0, "H135": 10.2, "H145": 11.0,
    "AS32": 18.7, "AS3B": 18.7,
    # Cargo / freighter specific 
    "A400": 42.4,
    # Russian
    "IL62": 43.2, "IL76": 50.5, "IL86": 48.06, "IL96": 60.1,
    "TU14": 21.0, "T134": 29.0, "T154": 37.6,
}


def parse_txt_file(path):
    """Parse a .txt aircraft file using configparser with [MODEL] section prepend."""
    config = configparser.ConfigParser()
    config.optionxform = str  # preserve case
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        config.read_string('[MODEL]\n' + content.replace('%', '%%'))
        return config['MODEL']
    except Exception:
        return None


def main():
    db = {}  # icao -> wingspan
    from_db = 0
    skipped_non_ifr = 0

    for group_dir in os.listdir(SRC_DIR):
        group_path = os.path.join(SRC_DIR, group_dir)
        if not os.path.isdir(group_path):
            continue

        for manufacturer in os.listdir(group_path):
            manufacturer_path = os.path.join(group_path, manufacturer)
            if not os.path.isdir(manufacturer_path):
                continue

            for aircraft_type in os.listdir(manufacturer_path):
                type_dir = os.path.join(manufacturer_path, aircraft_type)
                if not os.path.isdir(type_dir):
                    continue

                base_file = os.path.join(type_dir, aircraft_type + ".txt")
                if not os.path.isfile(base_file):
                    continue

                cfg = parse_txt_file(base_file)
                if cfg is None:
                    continue

                eng_type = cfg.get('ENG_TYPE', '').upper()
                if eng_type not in ('J', 'T'):
                    skipped_non_ifr += 1
                    # Still process variants but skip if base not IFR
                    # (variant inherits eng_type from base)
                    continue

                icao = cfg.get('ICAO', '').strip().upper()
                wingspan_str = cfg.get('WINGSPAN', '').strip()
                base_wingspan = float(wingspan_str) if wingspan_str else None

                if icao and base_wingspan is not None:
                    if icao not in db:
                        db[icao] = base_wingspan
                        from_db += 1

                # Process variants
                variants_dir = os.path.join(type_dir, "Variants")
                if os.path.exists(variants_dir):
                    for variant_file in os.listdir(variants_dir):
                        if os.path.isdir(os.path.join(variants_dir, variant_file)):
                            continue
                        if not variant_file.endswith('.txt'):
                            continue

                        vcfg = parse_txt_file(os.path.join(variants_dir, variant_file))
                        if vcfg is None:
                            continue

                        vicao = vcfg.get('ICAO', '').strip().upper()
                        vwingspan_str = vcfg.get('WINGSPAN', '').strip()
                        # Inherit wingspan from base if not in variant
                        vwingspan = float(vwingspan_str) if vwingspan_str else base_wingspan

                        if vicao and vwingspan is not None:
                            if vicao not in db:
                                db[vicao] = vwingspan
                                from_db += 1

    # Merge fallback — only fill gaps
    from_fallback = 0
    for icao, ws in AIRCRAFT_WINGSPANS.items():
        if icao not in db:
            db[icao] = ws
            from_fallback += 1

    # Sort alphabetically
    sorted_db = dict(sorted(db.items()))

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(sorted_db, f, indent=2)

    print(f"aircraft_wingspans.json created.")
    print(f"  Total types  : {len(sorted_db)}")
    print(f"  From DB      : {from_db}")
    print(f"  From fallback: {from_fallback}")
    print(f"  Skipped (non-IFR): {skipped_non_ifr}")


if __name__ == "__main__":
    main()
