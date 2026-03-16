import pdfplumber
import json
import sys
import os
import re

# Load wingspan data once
# Uses absolute path relative to this script to find the data folder
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WINGSPANS_PATH = os.path.join(SCRIPT_DIR, "..", "data", "aircraft_wingspans.json")
WINGSPANS = {}

if os.path.exists(WINGSPANS_PATH):
    with open(WINGSPANS_PATH, "r", encoding="utf-8") as f:
        WINGSPANS = json.load(f)

def get_best_acft(max_acft_str):
    if not max_acft_str or max_acft_str == "–":
        return max_acft_str
    parts = re.split(r'[,\/\s]+', max_acft_str)
    best_acft = None
    max_ws = -1.0
    for part in parts:
        acft = part.strip().upper()
        if not acft: continue
        ws = WINGSPANS.get(acft, 0.0)
        if ws > max_ws:
            max_ws = ws
            best_acft = acft
    if not best_acft and parts:
        return parts[0].strip().upper()
    return best_acft

def parse_excludes(remarks):
    if not remarks or "INCOMP" not in remarks.upper():
        return []
    match = re.search(r'INCOMP\.?\s*(.*)', remarks, re.IGNORECASE)
    if not match: return []
    raw_excl = match.group(1).strip()
    parts = re.split(r'[,\/\s]+', raw_excl)
    excludes = []
    for part in parts:
        clean = part.strip().strip('.')
        if clean and clean.upper() != "NONE":
            if '-' in clean:
                range_parts = clean.split('-')
                excludes.extend([p.strip() for p in range_parts if p.strip()])
            else:
                excludes.append(clean)
    return list(set(excludes))

def parse_range(range_str, available_keys):
    targets = set()
    parts = range_str.split(',')
    for part in parts:
        part = part.strip()
        if not part: continue
        if '-' in part:
            try:
                start_str, end_str = part.split('-')
                start = int(re.sub(r'\D', '', start_str))
                end = int(re.sub(r'\D', '', end_str))
                for i in range(start, end + 1):
                    targets.add(str(i))
            except: pass
        else:
            num = re.sub(r'\D', '', part)
            if num: targets.add(num)
            else: targets.add(part.upper())

    matched = []
    for key in available_keys:
        if key.upper() in targets:
            matched.append(key)
            continue
        num_key = re.sub(r'\D', '', key)
        if num_key:
            try:
                if str(int(num_key)) in targets:
                    matched.append(key)
            except: pass
    return matched

def get_pending_count(data, field):
    return sum(1 for v in data.values() if v[field] == "PENDIENTE")

def interactive_config(data):
    keys = list(data.keys())
    print("\n" + "="*40)
    print("      CONFIGURACIÓN INTERACTIVA")
    print("="*40)
    print("Formatos aceptados: '1-10, 15, 22'")
    print("Pulsa ENTER sin escribir nada para terminar una sección.")

    # 1. Terminales
    while True:
        pending = get_pending_count(data, "terminal")
        print(f"\nTerminales pendientes: {pending}/{len(keys)}")
        term = input("Nombre de Terminal (ej: T1, T2, Cargo) [ENTER para saltar]: ").strip()
        if not term: break
        rng = input(f"Rango de stands para {term}: ").strip()
        matched = parse_range(rng, keys)
        for k in matched: data[k]["terminal"] = term
        print(f"OK: {len(matched)} stands asignados a {term}")

    # 2. Schengen
    schengen_options = {"1": "schengen_only", "2": "non_schengen_only", "3": "mixed", "4": "ga"}
    while True:
        pending = get_pending_count(data, "schengen")
        print(f"\nZonas Schengen pendientes: {pending}/{len(keys)}")
        print("1: schengen_only | 2: non_schengen_only | 3: mixed | 4: ga")
        opt = input("Selecciona tipo (1-4) [ENTER para saltar]: ").strip()
        if not opt or opt not in schengen_options: break
        val = schengen_options[opt]
        rng = input(f"Rango de stands para {val}: ").strip()
        matched = parse_range(rng, keys)
        for k in matched: data[k]["schengen"] = val
        print(f"OK: {len(matched)} stands asignados a {val}")

    # 3. Remotos
    while True:
        pending = get_pending_count(data, "remote")
        print(f"\nEstado remoto pendiente: {pending}/{len(keys)}")
        rem = input("¿Son remotos? (s/n) [ENTER para saltar]: ").strip().lower()
        if not rem: break
        val = True if rem == 's' else False
        rng = input(f"Rango de stands para remote={val}: ").strip()
        matched = parse_range(rng, keys)
        for k in matched: data[k]["remote"] = val
        print(f"OK: {len(matched)} stands marcados como remote={val}")

def extract_pdf_data(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: No se encuentra el archivo '{pdf_path}'")
        return

    extracted_dict = {}
    # El archivo se genera en el mismo directorio que el script (.py)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_json = os.path.join(SCRIPT_DIR, f"{base_name}.json")

    print(f"Procesando PDF: {pdf_path}...")
    last_table_was_parking = False
    last_indices = None

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    last_table_was_parking = False
                    continue
                for table in tables:
                    if not table or not any(table[0]): continue
                    header = table[0]
                    idx_prkg, idx_max_acft, idx_remarks = -1, -1, -1
                    for i, h in enumerate(header):
                        if not h: continue
                        h_upper = str(h).upper()
                        if "PRKG" in h_upper: idx_prkg = i
                        elif "MAX ACFT" in h_upper: idx_max_acft = i
                        elif "REMARKS" in h_upper or "OBSERVACIONES" in h_upper: idx_remarks = i
                    
                    if idx_prkg != -1 and idx_max_acft != -1:
                        last_table_was_parking, last_indices = True, (idx_prkg, idx_max_acft, idx_remarks)
                        rows = table[1:]
                    elif last_table_was_parking and last_indices:
                        idx_prkg, idx_max_acft, idx_remarks = last_indices
                        rows = table
                    else:
                        last_table_was_parking = False
                        continue

                    for row in rows:
                        if not row or len(row) <= max(idx_prkg, idx_max_acft): continue
                        pid = str(row[idx_prkg]).strip() if row[idx_prkg] else ""
                        if not pid or "PRKG" in pid.upper() or "PARKING" in pid.upper(): continue
                        max_raw = str(row[idx_max_acft]).replace("\n", " ").strip() if row[idx_max_acft] else ""
                        rem_raw = ""
                        if idx_remarks != -1 and idx_remarks < len(row):
                            rem_raw = str(row[idx_remarks]).replace("\n", " ").strip() if row[idx_remarks] else ""
                        
                        extracted_dict[pid] = {
                            "max_acft": get_best_acft(max_raw),
                            "terminal": "PENDIENTE",
                            "schengen": "PENDIENTE",
                            "remote": "PENDIENTE",
                            "excludes": parse_excludes(rem_raw)
                        }

        if extracted_dict:
            interactive_config(extracted_dict)

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(extracted_dict, f, indent=4, ensure_ascii=False)

        print(f"\nFinalizado. Archivo guardado en: {output_json}")

    except Exception as e:
        print(f"Error durante el proceso: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_to_json.py <ruta_del_pdf>")
    else:
        extract_pdf_data(sys.argv[1])
