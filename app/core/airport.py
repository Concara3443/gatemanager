"""airport.py — Airport data container."""
import os

AIRPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'airports')


class AirportData:
    """Loads and holds all data for a specific airport."""

    def __init__(self, icao: str):
        self.icao = icao.upper()
        base = os.path.join(AIRPORTS_DIR, self.icao)
        from app import parking_finder as pf
        self.airlines  = pf.load_json(os.path.join(base, 'airlines.json'),  'airlines.json')
        self.wingspans = pf.load_json(os.path.join(base, 'aircraft_wingspans.json'), 'aircraft_wingspans.json')
        self.parkings  = pf.load_json(os.path.join(base, 'parkings.json'),  'parkings.json')
        pf._build_dedicated(self.airlines)
        pf._build_suffix_map(self.wingspans)

    @staticmethod
    def available() -> list:
        """Returns list of available airport ICAOs."""
        if not os.path.isdir(AIRPORTS_DIR):
            return []
        return [d for d in os.listdir(AIRPORTS_DIR)
                if os.path.isdir(os.path.join(AIRPORTS_DIR, d))]
