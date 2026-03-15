# airport data container
import os, sys

def _resource(path):
    # handle PyInstaller _MEIPASS temp folder
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    # if we are in app/core, we need to go up twice to reach root
    if not hasattr(sys, '_MEIPASS'):
        base = os.path.join(base, '..', '..')
    return os.path.join(base, path)

AIRPORTS_DIR = _resource('airports')
DATA_DIR     = _resource('data')

class AirportData:
    # load/hold data for specific airport
    def __init__(self, icao: str):
        self.icao = icao.upper(); base = os.path.join(AIRPORTS_DIR, self.icao)
        from app import parking_finder as pf
        self.config    = pf.load_json(os.path.join(base, 'config.json'),    'config.json')
        self.airlines  = pf.load_json(os.path.join(base, 'airlines.json'),  'airlines.json')
        self.wingspans = pf.load_json(os.path.join(DATA_DIR, 'aircraft_wingspans.json'), 'aircraft_wingspans.json')
        self.parkings  = pf.load_json(os.path.join(base, 'parkings.json'),  'parkings.json')
        # inject global cargo airlines (airport-level entry takes precedence)
        cargo_db = pf.load_json(os.path.join(DATA_DIR, 'cargo_airlines.json'), 'cargo_airlines.json')
        for code in cargo_db:
            if not code.startswith('_') and code not in self.airlines:
                self.airlines[code] = 'CARGO'
        default_term = self.config.get('terminals', [''])[0]
        pf._reset_globals()
        pf._build_dedicated(self.airlines, default_term)
        pf._build_labels(self.airlines, self.config.get('dedicated_airline_map', {}))
        pf._build_suffix_map(self.wingspans)
        # auto-fill max_wingspan from global db if not present in parkings.json
        for stand in self.parkings.values():
            if 'max_wingspan' not in stand:
                ws = self.wingspans.get(stand.get('max_acft', ''))
                if ws is not None:
                    stand['max_wingspan'] = ws

    @staticmethod
    def available() -> list:
        if not os.path.isdir(AIRPORTS_DIR): return []
        return [d for d in os.listdir(AIRPORTS_DIR) if os.path.isdir(os.path.join(AIRPORTS_DIR, d))]
