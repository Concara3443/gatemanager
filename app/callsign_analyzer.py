# check if callsign is private (GA) or commercial
import json, re, os, sys

def _data_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data', 'prefix_data.json')

# pattern overrides for empty json entries
_PATTERN_OVERRIDES = {
    # Brazil
    'PP': [{'len': 3, 'type': 'ALPHA'}],
    'PT': [{'len': 3, 'type': 'ALPHA'}],
    'PR': [{'len': 3, 'type': 'ALPHA'}],
    'PU': [{'len': 3, 'type': 'ALPHA'}],
    'PS': [{'len': 3, 'type': 'ALPHA'}],
    # Malta
    '9H': [{'len': 3, 'type': 'ALPHA'}],
    # San Marino
    'T7': [{'len': 3, 'type': 'ALPHA'}],
    # Senegal
    '6W': [{'len': 3, 'type': 'ALPHA'}],
    # Israel
    '4Z': [{'len': 3, 'type': 'ALPHA'}],
    # Vanuatu
    'YJ': [{'len': 3, 'type': 'ALPHA'}],
    # USA (N) - N + 1-5 alphanum
}

# skip corrupt or military prefixes
_SKIP_KEYS = {'code', 'plus', 'INSEE', 'FA'}


class CallsignAnalyzer:

    # icao airline pattern: 3 alpha + 1-4 alphanum (1st char digit)
    _AIRLINE_RE = re.compile(r'^[A-Z]{3}[A-Z0-9]{1,4}$')

    def __init__(self):
        with open(_data_path(), 'r', encoding='utf-8') as f:
            raw = json.load(f)

        self.data = {}
        for prefix, info in raw.items():
            if prefix in _SKIP_KEYS:
                continue
            if prefix in _PATTERN_OVERRIDES:
                info = dict(info)
                info['patterns'] = _PATTERN_OVERRIDES[prefix]
            self.data[prefix] = info

        # sort desc len to try longest prefixes first
        self.prefixes = sorted(self.data.keys(), key=len, reverse=True)

    def clean(self, cs):
        return cs.upper().replace('-', '').replace(' ', '')

    def check(self, callsign):
        clean = self.clean(callsign)

        if len(clean) < 3:
            return {'is_private': False, 'type': 'Invalid', 'countries': []}

        # 1. icao airline pattern: 3 alpha + digit → commercial
        if (self._AIRLINE_RE.match(clean)
                and clean[:3].isalpha()
                and len(clean) > 3
                and clean[3].isdigit()):
            return {'is_private': False, 'type': 'Airline', 'countries': []}

        # 2. prefix db search
        for prefix in self.prefixes:
            if not clean.startswith(prefix):
                continue
            suffix = clean[len(prefix):]
            if not suffix:
                continue

            info     = self.data[prefix]
            patterns = info.get('patterns', [])

            matched = False
            if patterns:
                for p in patterns:
                    if len(suffix) == p['len']:
                        if   p['type'] == 'ALPHA'    and suffix.isalpha():  matched = True
                        elif p['type'] == 'DIGIT'    and suffix.isdigit():  matched = True
                        elif p['type'] == 'ALPHANUM' and suffix.isalnum():  matched = True
            else:
                # fallback (N and FA): 2-5 alphanum
                if 2 <= len(suffix) <= 5 and suffix.isalnum():
                    matched = True

            if matched:
                # guard: short prefix + digit suffix usually means airline
                if len(prefix) <= 2 and suffix[0].isdigit() and prefix != 'N':
                    continue
                return {
                    'is_private': True,
                    'type': 'Registration',
                    'prefix': prefix,
                    'countries': info.get('countries', []),
                }

        # 3. USA registration (N + 2-5 alphanum)
        if clean.startswith('N') and 3 <= len(clean) <= 6 and clean[1:].isalnum():
            return {
                'is_private': True,
                'type': 'Registration (USA)',
                'prefix': 'N',
                'countries': ['United States'],
            }

        return {'is_private': False, 'type': 'Unknown / Airline', 'countries': []}
