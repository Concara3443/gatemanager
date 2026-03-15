# airport data container
import os

_HERE        = os.path.dirname(os.path.abspath(__file__))
AIRPORTS_DIR = os.path.join(_HERE, '..', '..', 'airports')
DATA_DIR     = os.path.join(_HERE, '..', '..', 'data')

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
        pf._build_dedicated(self.airlines); pf._build_suffix_map(self.wingspans)
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
