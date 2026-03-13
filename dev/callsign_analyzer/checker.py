import json
import re
import os

# Path to the data file
DATA_FILE = os.path.join(os.path.dirname(__file__), 'prefix_data.json')

class CallsignAnalyzer:
    def __init__(self):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        # Sort prefixes by length descending
        self.prefixes = sorted(self.data.keys(), key=len, reverse=True)
        
        # Common ICAO codes (3 letters) to rule out airlines
        # This is a small sample, could be expanded
        self.common_airlines = {
            'IBE', 'VLG', 'RYR', 'AEA', 'BAW', 'DLH', 'AFR', 'KLM', 'SWR', 
            'TAP', 'RAM', 'JAF', 'THY', 'PGT', 'QTR', 'UAE', 'ETD', 'ROT', 
            'LOT', 'SAS', 'FIN', 'NAX', 'NOZ', 'SVR', 'SBI', 'SWT', 'BCS', 
            'EXS', 'EZY', 'EJU', 'EZS', 'BEE', 'GWI', 'EWG', 'VLG', 'AEE'
        }

    def clean_callsign(self, callsign):
        # Convert to upper case and remove hyphens
        return callsign.upper().replace('-', '').replace(' ', '')

    def check(self, callsign):
        # 1. Clean: Uppercase, no hyphens, no spaces
        clean = self.clean_callsign(callsign)
        
        # 2. Skip obvious short or empty inputs
        if len(clean) < 3:
            return {'is_private': False, 'type': 'Invalid', 'callsign': clean}

        # 3. Rule out common airlines first (3-letter ICAO + alphanumeric)
        # Using a startswith check for the common ICAO list
        if len(clean) >= 4 and clean[:3].isalpha():
            if clean[:3] in self.common_airlines:
                return {
                    'is_private': False,
                    'type': 'Airline (Common ICAO)',
                    'icao': clean[:3],
                    'callsign': clean
                }

        # 4. Match with known prefixes (sorted by length DESC to catch 'VPA' before 'VP')
        for prefix in self.prefixes:
            if clean.startswith(prefix):
                suffix = clean[len(prefix):]
                
                # Suffix must exist for it to be a registration
                if not suffix:
                    continue
                
                info = self.data[prefix]
                patterns = info.get('patterns', [])
                
                matched = False
                if patterns:
                    for p in patterns:
                        if len(suffix) == p['len']:
                            if p['type'] == 'ALPHA' and suffix.isalpha():
                                matched = True
                            elif p['type'] == 'DIGIT' and suffix.isdigit():
                                matched = True
                            elif p['type'] == 'ALPHANUM' and suffix.isalnum():
                                matched = True
                else:
                    # Fallback: Most registrations have a suffix of 1-6 chars
                    if 1 <= len(suffix) <= 6 and suffix.isalnum():
                        matched = True
                
                if matched:
                    # Special check: even if prefix matches, if it's very short (1-2 chars)
                    # and the suffix looks like a flight number (starts with digit), 
                    # it might be an airline not in our list. 
                    # Except for USA (N) where it's always private.
                    if len(prefix) <= 2 and suffix[0].isdigit() and prefix != 'N':
                        # Likely a flight number (e.g., AA123, DL456)
                        continue

                    return {
                        'is_private': True,
                        'type': 'Registration',
                        'prefix': prefix,
                        'suffix': suffix,
                        'countries': info['countries'],
                        'callsign': clean
                    }
        
        # 5. Last resort: US Registration (N + 1-5 chars)
        if clean.startswith('N') and 2 <= len(clean) <= 6 and clean[1:].isalnum():
            return {
                'is_private': True,
                'type': 'Registration (USA)',
                'prefix': 'N',
                'suffix': clean[1:],
                'countries': ['United States'],
                'callsign': clean
            }

        return {
            'is_private': False,
            'type': 'Unknown / Airline',
            'callsign': clean
        }

if __name__ == "__main__":
    import sys
    analyzer = CallsignAnalyzer()
    
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            res = analyzer.check(arg)
            status = "PRIVADO (REG)" if res['is_private'] else "COMERCIAL/DESCONOCIDO"
            country = f" [{', '.join(res.get('countries', []))}]" if res['is_private'] else ""
            print(f"{arg} -> {status}{country} ({res['type']})")
    else:
        # Test cases
        test_cases = ["EC-LBS", "ECLBS", "IBE123", "N12345", "G-ABCD", "VLG4567", "EC-AA0", "OE-1234"]
        for tc in test_cases:
            res = analyzer.check(tc)
            status = "PRIVADO" if res['is_private'] else "COMERCIAL"
            country = f" ({', '.join(res.get('countries', []))})" if res['is_private'] else ""
            print(f"{tc:8} -> {status:8} {country:20} Type: {res['type']}")
