# parking finder — shared logic (GUI only)
import json
import os
import sys
import re

# Force UTF-8 output on Windows so box-drawing chars and colours work
if sys.platform == 'win32' and sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

# colors (used by resolve_aircraft_type and load_json)
R   = '\033[0m'
B   = '\033[1m'
DIM = '\033[2m'
CY  = '\033[96m'
GR  = '\033[92m'
YL  = '\033[93m'
RD  = '\033[91m'
MG  = '\033[95m'
WH  = '\033[97m'
BL  = '\033[94m'

# Data files
BASE           = os.path.dirname(os.path.abspath(__file__))
WINGSPANS_JSON = os.path.join(BASE, '..', 'data', 'aircraft_wingspans.json')

# schengen prefixes
SCHENGEN_PREFIXES = {
    'BI','EB','ED','ET','EE','EF','EH','EK','EL','EN',
    'EP','ES','EV','EY','LD','LE','GC','GE','LF','LG',
    'LH','LI','LJ','LK','LM','LO','LP','LS','LZ','LX',
}

# airline dedicated stands
DEDICATED          = {}  # code -> stands
DEDICATED_LABEL    = {}  # code -> label
DEDICATED_TERMINAL = {}  # code -> term
CURRENT_ICAO       = 'LEBL'

SUFFIX_MAP = {}  # suffix -> icao

_SCHENGEN_LABELS_BASE = {
    'schengen_only':     'Schengen',
    'non_schengen_only': 'Non-Sch.',
    'mixed':             'Mixed',
}
SCHENGEN_LABELS = dict(_SCHENGEN_LABELS_BASE)

_STANDARD_SCHENGEN = frozenset({'schengen_only', 'non_schengen_only', 'mixed', 'ga', 'maintenance', 'cargo'})


def _reset_globals():
    global DEDICATED, DEDICATED_LABEL, DEDICATED_TERMINAL, SUFFIX_MAP, SCHENGEN_LABELS
    DEDICATED.clear()
    DEDICATED_LABEL.clear()
    DEDICATED_TERMINAL.clear()
    SUFFIX_MAP.clear()
    SCHENGEN_LABELS.clear()
    SCHENGEN_LABELS.update(_SCHENGEN_LABELS_BASE)


def _build_dedicated(airlines_data, default_terminal=''):
    global DEDICATED, DEDICATED_LABEL, DEDICATED_TERMINAL
    for code, val in airlines_data.items():
        if isinstance(val, dict) and 'dedicated' in val:
            DEDICATED[code]          = set(val['dedicated'])
            DEDICATED_LABEL[code]    = val.get('label', f'{code} DEDICATED')
            DEDICATED_TERMINAL[code] = val.get('terminal', default_terminal)


def _build_labels(airlines_data, dedicated_airline_map):
    # populate SCHENGEN_LABELS with dedicated category display names
    # uses the label defined in airlines.json as-is
    for code, cat in dedicated_airline_map.items():
        if cat in SCHENGEN_LABELS:
            continue
        val = airlines_data.get(code)
        if isinstance(val, dict) and 'label' in val:
            SCHENGEN_LABELS[cat] = val['label']


def _build_suffix_map(wingspans_data):
    global SUFFIX_MAP
    for code in wingspans_data:
        suffix = code.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        if suffix:
            SUFFIX_MAP.setdefault(suffix, []).append(code)


def load_json(path, name):
    if not os.path.exists(path):
        print(f"{RD}ERROR:{R} {name} not found.")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_aircraft_type(raw, wingspans):
    # handle 738 -> B738; ask if multiple matches
    upper = raw.upper()
    if upper in wingspans:
        return upper
    matches = SUFFIX_MAP.get(upper)
    if not matches:
        return upper
    if len(matches) == 1:
        return matches[0]
    opts = '  /  '.join(matches)
    print(f"  {YL}'{raw}' matches several types: {WH}{opts}{R}")
    try:
        choice = input("  Specify full type: ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        return matches[0]
    return choice if choice in wingspans else matches[0]


def get_airline_terminals(airlines, code):
    # returns list of terminals or None; supports string, list, or object
    val = airlines.get(code)
    if val is None:
        return None
    t = val.get('terminal') if isinstance(val, dict) else val
    return t if isinstance(t, list) else [t]


def get_airline_terminal(airlines, code):
    ts = get_airline_terminals(airlines, code)
    return ts[0] if ts else None


def get_numeric_id(pid):
    m = re.match(r'^(\d+)', str(pid))
    return int(m.group(1)) if m else -1


def schengen_ok(data, schengen_flight):
    stype = data.get('schengen', 'mixed')
    if stype not in _STANDARD_SCHENGEN:
        # custom dedicated category — treated as mixed
        return True
    if schengen_flight:
        return stype != 'non_schengen_only'
    else:
        return stype != 'schengen_only'


def _sort_key(pid, data, prefer_type, _schengen_flight):
    ws     = data.get('max_wingspan')
    stype  = data.get('schengen', 'mixed')
    excl   = data.get('excludes', [])
    n_excl = len(excl)
    remote = data.get('remote', False)
    if ws is None:
        return (9999, 9999, 1, pid)
    preferred = (stype == prefer_type)
    gate_pen  = 0 if not remote else (0 if preferred else 1)
    return (ws, n_excl, gate_pen, pid)


def filter_parkings(parkings, terminal, airline_code, wingspan, schengen_flight, occupied, dedicated_map=None):
    # reverse map: schengen_category -> set of airlines allowed there
    cat_airlines = {}
    if dedicated_map:
        for a, c in dedicated_map.items():
            cat_airlines.setdefault(c, set()).add(a)

    result = {}
    for pid, data in parkings.items():
        if pid in occupied:
            continue
        if data.get('terminal') != terminal:
            continue
        stype = data.get('schengen', 'mixed')
        if stype in ('ga', 'maintenance', 'cargo'):
            continue
        if stype not in _STANDARD_SCHENGEN:
            if airline_code not in cat_airlines.get(stype, set()):
                continue
        max_ws = data.get('max_wingspan')
        if max_ws is not None and max_ws < wingspan:
            continue
        if not schengen_ok(data, schengen_flight):
            continue
        result[pid] = data
    return result
