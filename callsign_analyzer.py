"""callsign_analyzer.py — Detecta si un callsign es matrícula privada (GA) o vuelo comercial."""
import json, re, os, sys

def _data_path():
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'data', 'prefix_data.json')

# Patrones correctos para prefijos que el JSON tiene vacíos.
# Fuente: ICAO Annex 7 / registros nacionales oficiales.
_PATTERN_OVERRIDES = {
    # Brasil — PP/PT/PR/PU/PS + 3 letras
    'PP': [{'len': 3, 'type': 'ALPHA'}],
    'PT': [{'len': 3, 'type': 'ALPHA'}],
    'PR': [{'len': 3, 'type': 'ALPHA'}],
    'PU': [{'len': 3, 'type': 'ALPHA'}],
    'PS': [{'len': 3, 'type': 'ALPHA'}],
    # Malta — 9H + 3 letras
    '9H': [{'len': 3, 'type': 'ALPHA'}],
    # San Marino — T7 + 3 letras
    'T7': [{'len': 3, 'type': 'ALPHA'}],
    # Senegal (secundario) — 6W + 3 letras
    '6W': [{'len': 3, 'type': 'ALPHA'}],
    # Israel (secundario) — 4Z + 3 letras
    '4Z': [{'len': 3, 'type': 'ALPHA'}],
    # Vanuatu — YJ + 3 letras
    'YJ': [{'len': 3, 'type': 'ALPHA'}],
    # USA general (N) se deja sin patrón: N + 1-5 alphanum son todos válidos
    # FA (USA militar/gubernamental): muy improbable en IVAO, se deja sin patrón
}

# Entradas que se ignoran: corruptas o prefijos militares/especiales que
# jamás aparecen en ATC civil de IVAO y causarían falsos positivos.
# FA (aviones militares USA): conflicto con F (Francia) → F-ABCD se detectaría
# como FA+BCD (USA) en vez de F+ABCD (Francia).
_SKIP_KEYS = {'code', 'plus', 'INSEE', 'FA'}


class CallsignAnalyzer:

    # Patrón ICAO de aerolínea comercial: exactamente 3 letras + 1-4 alfanuméricos
    # donde el primer carácter tras las 3 letras es un dígito (número de vuelo).
    # Ejemplos: NDA2131, IBE3421, BAW234, UAL123, RYR4567
    _AIRLINE_RE = re.compile(r'^[A-Z]{3}[A-Z0-9]{1,4}$')

    def __init__(self):
        with open(_data_path(), 'r', encoding='utf-8') as f:
            raw = json.load(f)

        self.data = {}
        for prefix, info in raw.items():
            # Ignorar entradas corruptas
            if prefix in _SKIP_KEYS:
                continue
            # Aplicar parche de patrones si existe
            if prefix in _PATTERN_OVERRIDES:
                info = dict(info)
                info['patterns'] = _PATTERN_OVERRIDES[prefix]
            self.data[prefix] = info

        # Ordenar por longitud descendente para que prefijos largos se prueben primero
        self.prefixes = sorted(self.data.keys(), key=len, reverse=True)

        # Aerolíneas ICAO conocidas (3 letras). Ampliar si es necesario.
        self.common_airlines = {
            'IBE', 'VLG', 'RYR', 'AEA', 'BAW', 'DLH', 'AFR', 'KLM', 'SWR',
            'TAP', 'RAM', 'JAF', 'THY', 'PGT', 'QTR', 'UAE', 'ETD', 'ROT',
            'LOT', 'SAS', 'FIN', 'NAX', 'NOZ', 'SVR', 'SBI', 'SWT', 'BCS',
            'EXS', 'EZY', 'EJU', 'EZS', 'BEE', 'GWI', 'EWG', 'AEE', 'GOL',
            'TAM', 'AZU', 'GLO', 'ONE', 'NDA', 'UAL', 'DAL', 'AAL', 'SWA',
        }

    def clean(self, cs):
        return cs.upper().replace('-', '').replace(' ', '')

    def check(self, callsign):
        clean = self.clean(callsign)

        if len(clean) < 3:
            return {'is_private': False, 'type': 'Invalid', 'countries': []}

        # 1. Aerolíneas conocidas por código ICAO exacto
        if len(clean) >= 4 and clean[:3].isalpha() and clean[:3] in self.common_airlines:
            return {'is_private': False, 'type': 'Airline (ICAO)', 'countries': []}

        # 2. Patrón genérico de aerolínea ICAO: 3 letras exactas + primer char es dígito
        #    Cubre NDA2131, UAL234, FAB123, etc. aunque no estén en la lista conocida.
        if (self._AIRLINE_RE.match(clean)
                and clean[:3].isalpha()
                and len(clean) > 3
                and clean[3].isdigit()):
            return {'is_private': False, 'type': 'Airline (pattern)', 'countries': []}

        # 3. Búsqueda en base de datos de prefijos (longitud desc. para evitar
        #    que 'N' match antes que 'NO' o 'NL')
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
                # Fallback sin patrón definido (solo N y FA llegan aquí tras los parches).
                # Requiere sufijo 2-5 chars alfanumérico para evitar matches triviales.
                if 2 <= len(suffix) <= 5 and suffix.isalnum():
                    matched = True

            if matched:
                # Guardia extra: prefijo corto (1-2 chars) + sufijo empieza con dígito
                # → probablemente número de vuelo de aerolínea no catalogada.
                # Excepción: N (USA) donde N + dígitos es matrícula válida.
                if len(prefix) <= 2 and suffix[0].isdigit() and prefix != 'N':
                    continue
                return {
                    'is_private': True,
                    'type': 'Registration',
                    'prefix': prefix,
                    'countries': info.get('countries', []),
                }

        # 4. Última guardia: matrículas USA cortas no capturadas (N + 2-5 alphanum)
        if clean.startswith('N') and 3 <= len(clean) <= 6 and clean[1:].isalnum():
            return {
                'is_private': True,
                'type': 'Registration (USA)',
                'prefix': 'N',
                'countries': ['United States'],
            }

        return {'is_private': False, 'type': 'Unknown / Airline', 'countries': []}
