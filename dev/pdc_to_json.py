import pdfplumber
import json
import sys
import os
import re

# Directorio del script para guardar los outputs
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
    return best_acft if best_acft else (parts[0].strip().upper() if parts else max_acft_str)

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
    """
    Intelligently parses ranges like '100-101b' or '1,2,5-10'.
    If the start and end of a range are found in available_keys, it takes all stands between them.
    """
    sorted_keys = sorted(available_keys, key=lambda x: (re.sub(r'\D', '', x).zfill(5), x))
    matched_indices = set()

    parts = range_str.split(',')
    for part in parts:
        part = part.strip()
        if not part: continue

        if '-' in part:
            start_val, end_val = [p.strip().upper() for p in part.split('-')]

            # Find exact or near matches in sorted_keys
            start_idx = -1
            end_idx = -1

            for i, k in enumerate(sorted_keys):
                k_up = k.upper()
                # Match exact or numeric (e.g. "1" matches "01")
                if k_up == start_val or re.sub(r'\D', '', k_up).lstrip('0') == start_val.lstrip('0'):
                    if start_idx == -1: start_idx = i
                if k_up == end_val or re.sub(r'\D', '', k_up).lstrip('0') == end_val.lstrip('0'):
                    end_idx = i

            if start_idx != -1 and end_idx != -1:
                # If start is after end, swap them
                s, e = (start_idx, end_idx) if start_idx <= end_idx else (end_idx, start_idx)
                for i in range(s, e + 1):
                    matched_indices.add(i)
            else:
                # Fallback to pure numeric range if indices not found
                try:
                    s_num = int(re.sub(r'\D', '', start_val))
                    e_num = int(re.sub(r'\D', '', end_val))
                    for i, k in enumerate(sorted_keys):
                        k_num_str = re.sub(r'\D', '', k)
                        if k_num_str:
                            k_num = int(k_num_str)
                            if min(s_num, e_num) <= k_num <= max(s_num, e_num):
                                matched_indices.add(i)
                except: pass
        else:
            # Single stand match
            val = part.upper()
            for i, k in enumerate(sorted_keys):
                k_up = k.upper()
                if k_up == val or re.sub(r'\D', '', k_up).lstrip('0') == val.lstrip('0'):
                    matched_indices.add(i)

    return [sorted_keys[i] for i in matched_indices]

def show_status(data):
    keys = list(data.keys())
    t_pend = [k for k, v in data.items() if v["terminal"] == "PENDIENTE"]
    s_pend = [k for k, v in data.items() if v["schengen"] == "PENDIENTE"]
    r_pend = [k for k, v in data.items() if v["remote"] == "PENDIENTE"]
    
    print("\n" + "="*50)
    print(f" ESTADO ACTUAL ({len(keys)} stands totales)")
    print("="*50)
    print(f" Terminales: {len(keys)-len(t_pend)} ok / {len(t_pend)} pendientes")
    print(f" Schengen:   {len(keys)-len(s_pend)} ok / {len(s_pend)} pendientes")
    print(f" Remotos:    {len(keys)-len(r_pend)} ok / {len(r_pend)} pendientes")
    print("-" * 50)

def interactive_config(data):
    keys = sorted(list(data.keys()))
    
    while True:
        show_status(data)
        print("MENÚ PRINCIPAL:")
        print("1. Configurar TERMINALES")
        print("2. Configurar ZONAS SCHENGEN")
        print("3. Configurar ESTADO REMOTO")
        print("4. Ver stands PENDIENTES (lista detallada)")
        print("5. Ver RESUMEN completo de asignaciones")
        print("6. GUARDAR Y FINALIZAR")
        
        opc = input("\nSelecciona una opción: ").strip()
        
        if opc == "1":
            while True:
                pend = [k for k in keys if data[k]["terminal"] == "PENDIENTE"]
                print(f"\n[TERMINALES] Pendientes ({len(pend)}): {', '.join(pend[:20])}{'...' if len(pend)>20 else ''}")
                val = input("Nombre Terminal (ej: T1) [ENTER para volver]: ").strip()
                if not val: break
                rng = input(f"Stands para {val}: ").strip()
                matched = parse_range(rng, keys)
                for k in matched: data[k]["terminal"] = val
                print(f"OK: {len(matched)} stands asignados a {val}")

        elif opc == "2":
            opts = {"1": "schengen_only", "2": "non_schengen_only", "3": "mixed", "4": "ga"}
            while True:
                pend = [k for k in keys if data[k]["schengen"] == "PENDIENTE"]
                print(f"\n[SCHENGEN] Pendientes ({len(pend)}): {', '.join(pend[:20])}{'...' if len(pend)>20 else ''}")
                print("1: schengen_only | 2: non_schengen_only | 3: mixed | 4: ga")
                sub_opc = input("Selecciona tipo (1-4) [ENTER para volver]: ").strip()
                if not sub_opc or sub_opc not in opts: break
                val = opts[sub_opc]
                rng = input(f"Stands para {val}: ").strip()
                matched = parse_range(rng, keys)
                for k in matched: data[k]["schengen"] = val
                print(f"OK: {len(matched)} stands asignados a {val}")

        elif opc == "3":
            while True:
                pend = [k for k in keys if data[k]["remote"] == "PENDIENTE"]
                print(f"\n[REMOTO] Pendientes ({len(pend)}): {', '.join(pend[:20])}{'...' if len(pend)>20 else ''}")
                val_in = input("¿Son remotos? (s/n) [ENTER para volver]: ").strip().lower()
                if not val_in: break
                val = True if val_in == 's' else False
                rng = input(f"Stands para remote={val}: ").strip()
                matched = parse_range(rng, keys)
                for k in matched: data[k]["remote"] = val
                print(f"OK: {len(matched)} stands marcados como remote={val}")

        elif opc == "4":
            print("\n--- STANDS PENDIENTES ---")
            for field in ["terminal", "schengen", "remote"]:
                pend = [k for k in keys if data[k][field] == "PENDIENTE"]
                print(f"{field.upper()}: {', '.join(pend) if pend else '¡Nada pendiente!'}\n")
            input("Pulsa ENTER para volver...")

        elif opc == "5":
            print("\n--- RESUMEN DE ASIGNACIONES ---")
            print(f"{'Stand':<8} | {'Term':<8} | {'Schengen':<18} | {'Remote':<8}")
            print("-" * 55)
            for k in keys:
                d = data[k]
                print(f"{k:<8} | {d['terminal']:<8} | {d['schengen']:<18} | {str(d['remote']):<8}")
            input("\nPulsa ENTER para volver...")

        elif opc == "6":
            confirm = input("\n¿Seguro que quieres guardar y salir? (s/n): ").strip().lower()
            if confirm == 's': break

def extract_pdf_data(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"Error: No se encuentra '{pdf_path}'")
        return

    extracted_dict = {}
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_json = os.path.join(SCRIPT_DIR, f"{base_name}.json")

    print(f"Extrayendo datos de {pdf_path}...")
    try:
        with pdfplumber.open(pdf_path) as pdf:
            last_table_was_parking, last_indices = False, None
            for page in pdf.pages:
                tables = page.extract_tables()
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
            print(f"\nArchivo guardado en: {output_json}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python pdf_to_json.py <ruta_pdf>")
    else:
        extract_pdf_data(sys.argv[1])
