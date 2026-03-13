import csv
import re
import json

def clean_prefix(p):
    # Remove everything after a space, bracket or parenthesis
    p = re.split(r'[\s\[\(\,]', p)[0]
    # Remove hyphen
    p = p.replace('-', '')
    return p.strip()

def parse_regs(csv_path):
    prefixes = {}
    last_country = ""
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        next(f) # Skip Column1;...
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            country = row.get('Country or region', '').strip()
            if not country:
                country = last_country
            else:
                last_country = country
                
            raw_prefix = row.get('Registration prefix', '').strip()
            if not raw_prefix:
                continue
                
            # Handle multiple prefixes in one cell (separated by comma or space)
            raw_parts = re.split(r'[\,\s]+', raw_prefix)
            for part in raw_parts:
                prefix = clean_prefix(part)
                if not prefix or len(prefix) > 5: # Safety check
                    continue
                    
                notes = row.get('Presentation and notes', '')
                
                if prefix not in prefixes:
                    prefixes[prefix] = {
                        'countries': [],
                        'patterns': []
                    }
                
                if country not in prefixes[prefix]['countries']:
                    prefixes[prefix]['countries'].append(country)
                
                # Enhanced pattern extraction
                clean_notes = notes.replace('-', '')
                
                # 1. Match "PREFIX-AAA to PREFIX-ZZZ" or similar
                found_to = re.findall(rf'{prefix}([A-Z0-9]+)\s+to\s+{prefix}([A-Z0-9]+)', clean_notes)
                for p_start, p_end in found_to:
                    if len(p_start) == len(p_end):
                        p_type = 'ALPHA' if p_start.isalpha() else ('DIGIT' if p_start.isdigit() else 'ALPHANUM')
                        pattern_info = {'len': len(p_start), 'type': p_type}
                        if pattern_info not in prefixes[prefix]['patterns']:
                            prefixes[prefix]['patterns'].append(pattern_info)
                
                # 2. Match "followed by three or five numbers" (Armenia case)
                if "three" in notes.lower() and "numbers" in notes.lower():
                    prefixes[prefix]['patterns'].append({'len': 3, 'type': 'DIGIT'})
                if "five" in notes.lower() and "numbers" in notes.lower():
                    prefixes[prefix]['patterns'].append({'len': 5, 'type': 'DIGIT'})
                
                # 3. Match explicit numeric ranges like "10000 to 99999"
                found_nums = re.findall(r'(\d+)\s+to\s+(\d+)', clean_notes)
                for n_start, n_end in found_nums:
                    if len(n_start) == len(n_end):
                        pattern_info = {'len': len(n_start), 'type': 'DIGIT'}
                        if pattern_info not in prefixes[prefix]['patterns']:
                            prefixes[prefix]['patterns'].append(pattern_info)
    
    return prefixes

if __name__ == "__main__":
    data = parse_regs('regs.csv')
    with open('callsign_analyzer/prefix_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Parsed {len(data)} prefixes.")
