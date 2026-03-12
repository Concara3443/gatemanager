"""
parking_finder.py
LEBL Barcelona Parking Assignment System for IVAO virtual ATC.

Usage:
    python parking_finder.py              # interactive session (loops until quit)
    python parking_finder.py AEA B738 LFPO  # single query, then exit
"""
import json
import os
import sys
import re
from aurora_bridge import AuroraBridge, callsign_to_airline

# Force UTF-8 output on Windows so box-drawing chars and colours work
if sys.platform == 'win32' and sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

# ─── ANSI colours ────────────────────────────────────────────────────────────
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

# ─── Data files ───────────────────────────────────────────────────────────────
BASE           = os.path.dirname(os.path.abspath(__file__))
DATA           = os.path.join(BASE, "data")
AIRLINES_JSON  = os.path.join(DATA, "airlines.json")
WINGSPANS_JSON = os.path.join(DATA, "aircraft_wingspans.json")
PARKINGS_JSON  = os.path.join(DATA, "parkings.json")

# ─── Schengen prefix lookup ───────────────────────────────────────────────────
SCHENGEN_PREFIXES = {
    'BI','LB','LD','LE','LF','LG','LH','LI','LJ','LK','LM',
    'LO','LP','LS','LZ','EB','ED','EF','EH','EK','EL','EN',
    'EP','ES','EV','EY',
}
NON_SCHENGEN_PREFIXES = {
    'EG','EI','LQ','LR','LT','LU','LW','LX','LY', 'GM'
}

# ─── Special airline dedicated stands (populated from airlines.json at startup)
DEDICATED          = {}  # code -> set of stand IDs
DEDICATED_LABEL    = {}  # code -> display label
DEDICATED_TERMINAL = {}  # code -> terminal


def _build_dedicated(airlines_data):
    """Populate DEDICATED dicts from airlines.json entries that have a 'dedicated' key."""
    global DEDICATED, DEDICATED_LABEL, DEDICATED_TERMINAL
    for code, val in airlines_data.items():
        if isinstance(val, dict) and 'dedicated' in val:
            DEDICATED[code]          = set(val['dedicated'])
            DEDICATED_LABEL[code]    = val.get('label', f'{code} DEDICATED')
            DEDICATED_TERMINAL[code] = val.get('terminal', 'T1')


def _build_suffix_map(wingspans_data):
    """Build numeric suffix -> [ICAO codes] map. '738' -> ['B738'], '320' -> ['A320', ...]."""
    global SUFFIX_MAP
    for code in wingspans_data:
        suffix = code.lstrip('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        if suffix:
            SUFFIX_MAP.setdefault(suffix, []).append(code)


def resolve_aircraft_type(raw, wingspans):
    """Allow shorthand input: '738' -> 'B738', '320' -> 'A320', etc.
    If multiple codes share the same suffix, ask the user to specify."""
    upper = raw.upper()
    if upper in wingspans:
        return upper
    matches = SUFFIX_MAP.get(upper)
    if not matches:
        return upper  # unknown, will prompt for wingspan later
    if len(matches) == 1:
        return matches[0]
    # Multiple matches — ask user to pick
    opts = '  /  '.join(matches)
    print(f"  {YL}'{raw}' matches several types: {WH}{opts}{R}")
    try:
        choice = input(f"  Specify full type: ").strip().upper()
    except (EOFError, KeyboardInterrupt):
        return matches[0]
    return choice if choice in wingspans else matches[0]


def get_airline_terminal(airlines, code):
    """Return terminal string ('T1', 'T2', 'CARGO') or None if airline unknown."""
    val = airlines.get(code)
    if val is None:
        return None
    if isinstance(val, dict):
        return val.get('terminal')
    return val

SUFFIX_MAP = {}  # numeric suffix -> full ICAO type (e.g. '738' -> 'B738')

WIDEBODY_THRESHOLD = 55.0
SCHENGEN_LABELS = {
    'schengen_only':    'Schengen',
    'non_schengen_only':'Non-Sch.',
    'mixed':            'Mixed',
    'ibe_dedicated':    'IBERIA',
    'eju_ezy_ezs':      'EASYJET',
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path, name):
    if not os.path.exists(path):
        print(f"{RD}ERROR:{R} {name} not found. Run build scripts first.")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_wingspan(aircraft_type, wingspans):
    """Get wingspan for aircraft_type. If not in dict, ask user and save to JSON."""
    wingspan = wingspans.get(aircraft_type)
    if wingspan is None:
        print(f"\n  {YL}Aircraft '{aircraft_type}' not in database.{R}")
        try:
            val = input("  Wingspan in metres: ").strip()
            if not val:
                return 36.0
            wingspan = float(val)
        except (ValueError, EOFError, KeyboardInterrupt):
            wingspan = 36.0

        # Save to database
        wingspans[aircraft_type] = wingspan
        try:
            # Sort keys so the file stays organized
            sorted_ws = dict(sorted(wingspans.items()))
            with open(WINGSPANS_JSON, 'w', encoding='utf-8') as f:
                json.dump(sorted_ws, f, indent=2)
            print(f"  {GR}Saved {aircraft_type}={wingspan}m to database.{R}")
        except Exception as e:
            print(f"  {RD}Error saving to database: {e}{R}")

    return wingspan


def get_numeric_id(pid):
    m = re.match(r'^(\d+)', str(pid))
    return int(m.group(1)) if m else -1


def is_schengen_flight(icao_origin, interactive=True):
    prefix = icao_origin[:2].upper() if icao_origin and len(icao_origin) >= 2 else None
    if prefix in SCHENGEN_PREFIXES:
        return True, prefix
    if prefix in NON_SCHENGEN_PREFIXES:
        return False, prefix
    european = {'E', 'L', 'B', 'G', 'F', 'O', 'H', 'D'}
    if prefix and prefix[0] not in european:
        return False, prefix
    if interactive:
        print(f"  {YL}Unknown Schengen status for prefix '{prefix}' ({icao_origin}).{R}")
        ans = input("  Schengen flight? (y/n): ").strip().lower()
        return (ans == 'y'), prefix
    return None, prefix


def _country(prefix):
    c = {
        'BI':'Iceland',  'LB':'Bulgaria', 'LD':'Croatia',  'LE':'Spain',
        'LF':'France',   'LG':'Greece',   'LH':'Hungary',  'LI':'Italy',
        'LJ':'Slovenia', 'LK':'Czech Rep.','LM':'Malta',   'LO':'Austria',
        'LP':'Portugal', 'LS':'Switzerland','LZ':'Slovakia',
        'EB':'Belgium',  'ED':'Germany',  'EF':'Finland',  'EH':'Netherlands',
        'EK':'Denmark',  'EL':'Luxembourg','EN':'Norway',  'EP':'Poland',
        'ES':'Sweden',   'EV':'Latvia',   'EY':'Lithuania',
        'EG':'United Kingdom', 'EI':'Ireland',
        'LQ':'Bosnia',   'LR':'Romania',  'LT':'Turkey',   'LU':'Moldova',
        'LW':'N. Macedonia', 'LX':'Gibraltar', 'LY':'Serbia',
    }
    return c.get(prefix, prefix or '?')


def schengen_ok(data, schengen_flight):
    stype  = data.get('schengen', 'mixed')
    remote = data.get('remote', False)
    if stype in ('ibe_dedicated', 'eju_ezy_ezs'):
        if not remote and not schengen_flight:
            return False
        return True
    if schengen_flight:
        return stype != 'non_schengen_only'
    else:
        return stype != 'schengen_only'


def _sort_key(pid, data, prefer_type, _schengen_flight):
    """Sort by: tightest wingspan fit → fewest exclusions → gate before remote → id.
    A remote with exact wingspan match always beats a gate with excess capacity."""
    ws     = data.get('max_wingspan')
    stype  = data.get('schengen', 'mixed')
    excl   = data.get('excludes', [])
    n_excl = len(excl)
    remote = data.get('remote', False)
    if ws is None:
        return (9999, 9999, 1, pid)
    preferred = (stype == prefer_type)
    gate_pen = 0 if not remote else (0 if preferred else 1)
    return (ws, n_excl, gate_pen, pid)


def filter_parkings(parkings, terminal, airline_code, wingspan, schengen_flight, occupied):
    result = {}
    for pid, data in parkings.items():
        if pid in occupied:
            continue
        if data.get('terminal') != terminal:
            continue
        stype = data.get('schengen', 'mixed')
        if stype in ('ga', 'maintenance', 'cargo'):
            continue
        if stype == 'eju_ezy_ezs' and airline_code not in ('EJU', 'EZY', 'EZS'):
            continue
        if stype == 'ibe_dedicated' and airline_code != 'IBE':
            continue
        max_ws = data.get('max_wingspan')
        if max_ws is not None and max_ws < wingspan:
            continue
        if not schengen_ok(data, schengen_flight):
            continue
        result[pid] = data
    return result


def info_stand(pid, parkings, occupied, airline_code=None, aircraft_type=None, origin=None, airlines=None, wingspans=None):
    if pid not in parkings:
        print(f"  {RD}Stand '{pid}' not found.{R}")
        return

    data = parkings[pid]
    ws = data.get('max_wingspan')
    max_acft = data.get('max_acft', '?')
    stype = data.get('schengen', 'mixed')
    term = data.get('terminal', 'T1')
    remote = data.get('remote', False)
    excl = data.get('excludes', [])

    _box_top(f"INFO: STAND {pid}")
    print()
    _info_row("Terminal", f"{term}")
    _info_row("Type", "Remote" if remote else "Gate")
    _info_row("Max Acft", f"{max_acft}")
    _info_row("Max WS", f"{ws} m")
    _info_row("Schengen", SCHENGEN_LABELS.get(stype, stype))
    if excl:
        _info_row("Excludes", ", ".join(excl))

    status = f"{RD}OCCUPIED{R}" if pid in occupied else f"{GR}AVAILABLE{R}"
    _info_row("Status", status)

    if airline_code and aircraft_type and origin:
        print(f"\n  {B}Suitability for {airline_code} {aircraft_type} from {origin}:{R}")

        # Check Wingspan
        acft_ws = get_wingspan(aircraft_type, wingspans)
        ws_ok = (ws is None or ws >= acft_ws)
        ws_str = f"{GR}OK{R}" if ws_ok else f"{RD}TOO SMALL{R} (needs {acft_ws}m)"
        _info_row("Wingspan", f"{ws_str} ({acft_ws}m)")

        # Check Schengen
        sch_bool, sch_prefix = is_schengen_flight(origin, interactive=True)
        if sch_bool is None:
             sch_str = f"{YL}UNKNOWN{R}"
             sch_ok_val = True
        else:
            sch_ok_val = schengen_ok(data, sch_bool)
            sch_str = f"{GR}OK{R}" if sch_ok_val else f"{RD}NOT ALLOWED{R} ({SCHENGEN_LABELS.get(stype, stype)})"

        _info_row("Schengen", sch_str)

        # Check Terminal
        airline_term = get_airline_terminal(airlines, airline_code)
        term_ok = (airline_term is None or airline_term == term or airline_term == 'CARGO')
        term_str = f"{GR}OK{R}" if term_ok else f"{RD}WRONG TERMINAL{R} ({airline_code} uses {airline_term})"
        _info_row("Terminal", term_str)

        # Dedicated check
        dedicated_ok = True
        if stype == 'eju_ezy_ezs' and airline_code not in ('EJU', 'EZY', 'EZS'):
            dedicated_ok = False
        if stype == 'ibe_dedicated' and airline_code != 'IBE':
            dedicated_ok = False

        if not dedicated_ok:
             _info_row("Dedicated", f"{RD}RESTRICTED{R} (Only for {'EasyJet' if stype.startswith('eju') else 'Iberia'})")

        if ws_ok and sch_ok_val and term_ok and dedicated_ok:
            print(f"\n  {GR}{B}✓ STAND IS SUITABLE{R}")
        else:
            print(f"\n  {RD}{B}✗ STAND IS NOT SUITABLE{R}")

    print()


# ─── Display ─────────────────────────────────────────────────────────────────

WIDTH = 62

def _box_top(title):
    inner = WIDTH - 2
    pad   = (inner - len(title)) // 2
    print(f"{CY}╔{'═' * inner}╗{R}")
    print(f"{CY}║{' ' * pad}{B}{WH}{title}{R}{CY}{' ' * (inner - pad - len(title))}║{R}")
    print(f"{CY}╚{'═' * inner}╝{R}")


def _info_row(label, value):
    print(f"  {DIM}{label:<10}{R} {WH}{B}{value}{R}")


def _section_header(title, count):
    bar = '─' * max(2, WIDTH - len(title) - len(str(count)) - 7)
    print(f"\n  {BL}{B}{title}{R}  {DIM}{count} option{'s' if count != 1 else ''}{R}  {DIM}{bar}{R}")


def _warn(msg):
    print(f"\n  {RD}{B}⚠  {msg}{R}")


def _note(msg):
    print(f"  {DIM}ℹ  {msg}{R}")


RESULTS_LIMIT = 10  # default max rows shown; type '+' at the prompt to see all


def print_table(pids, data_map, schengen_flight, limit=RESULTS_LIMIT, acft_ws=None):
    """Render sorted table. Returns (visible_pids, all_sorted_pids)."""
    prefer = 'schengen_only' if schengen_flight else 'non_schengen_only'
    all_sorted = sorted(
        pids,
        key=lambda p: _sort_key(p, data_map[p], prefer, schengen_flight)
    )
    visible = all_sorted if limit is None else all_sorted[:limit]
    hidden  = len(all_sorted) - len(visible)

    cols = ['Stand', 'Max WS', 'Type', 'Zone', 'Excludes']
    rows = []
    perfect = set()
    for pid in visible:
        d      = data_map[pid]
        ws     = d.get('max_wingspan')
        excl   = d.get('excludes', [])
        remote = d.get('remote', False)
        fit    = acft_ws is not None and ws is not None and ws == acft_ws
        if fit:
            perfect.add(pid)
        rows.append([
            pid,
            (f"{ws} m ★" if ws is not None else "?") if fit else (f"{ws} m" if ws is not None else "?"),
            'Remote' if remote else 'Gate',
            SCHENGEN_LABELS.get(d.get('schengen', 'mixed'), ''),
            ', '.join(excl) if excl else '-',
        ])

    cw = [len(c) for c in cols]
    for row in rows:
        for i, cell in enumerate(row):
            cw[i] = max(cw[i], len(str(cell)))

    def colour_row(row, data, is_perfect):
        remote = data.get('remote', False)
        excl   = data.get('excludes', [])
        cells  = []
        for i, cell in enumerate(row):
            s   = str(cell)
            pad = cw[i] - len(s)
            if i == 0:
                col = f"{B}{MG}{s}{R}" if is_perfect else f"{B}{WH}{s}{R}"
            elif i == 1:
                col = f"{B}{MG}{s}{R}" if is_perfect else f"{CY}{s}{R}"
            elif i == 2:
                col = f"{YL}{s}{R}" if remote else f"{GR}{s}{R}"
            elif i == 3:
                col = f"{DIM}{s}{R}"
            elif i == 4:
                col = f"{RD}{s}{R}" if excl else f"{DIM}{s}{R}"
            else:
                col = s
            cells.append(f' {col}{" " * pad} ')
        return '│'.join(cells)

    def plain_row(r):
        return '│' + '│'.join(f' {str(c):<{cw[i]}} ' for i, c in enumerate(r)) + '│'

    top     = '┌' + '┬'.join('─' * (w + 2) for w in cw) + '┐'
    sep     = '├' + '┼'.join('─' * (w + 2) for w in cw) + '┤'
    hdr_sep = '├' + '┼'.join('═' * (w + 2) for w in cw) + '┤'
    bot     = '└' + '┴'.join('─' * (w + 2) for w in cw) + '┘'

    print(f"  {DIM}{top}{R}")
    print(f"  {DIM}{plain_row(cols)}{R}")
    print(f"  {DIM}{hdr_sep}{R}")

    has_excl = False
    for idx, (pid, row) in enumerate(zip(visible, rows)):
        d          = data_map[pid]
        excl       = d.get('excludes', [])
        is_perfect = pid in perfect
        if excl:
            has_excl = True
        print(f"  {DIM}│{R}{colour_row(row, d, is_perfect)}{DIM}│{R}")
        if idx < len(rows) - 1:
            print(f"  {DIM}{sep}{R}")

    print(f"  {DIM}{bot}{R}")

    if has_excl:
        print()
        _note("Stands with exclusions block adjacent positions when occupied.")

    if hidden:
        print(f"  {DIM}... {hidden} more not shown  (type + to see all){R}")

    return visible, all_sorted


def show_results(label, pids, data_map, schengen_flight, acft_ws=None, is_fallback=False):
    """Returns (visible_pids, all_sorted_pids)."""
    prefix = f"{YL}FALLBACK · {R}" if is_fallback else ""
    _section_header(f"{prefix}{label}", len(pids))
    print()
    visible, all_sorted = print_table(pids, data_map, schengen_flight, acft_ws=acft_ws)
    return visible, all_sorted


def assign_prompt(visible_pids, all_pids, data_map, schengen_flight, parkings, occupied, acft_ws=None, aurora=None, callsign=None):
    """Prompt user to assign a stand.
    Modifiers: r (remote only)  p (gates only)  + (show all)  r+ p+ (filter+all)
    Type a stand ID to assign it."""
    if not all_pids:
        return

    # active_pool: the currently filtered subset of all_pids
    active_pool  = list(all_pids)
    active_label = ""  # shown in prompt hint
    show_all     = False

    def _redisplay(pool, expand):
        lim = None if expand else RESULTS_LIMIT
        vis, _ = print_table(pool, data_map, schengen_flight, limit=lim, acft_ws=acft_ws)
        return vis

    while True:
        hint_parts = ["ID"]
        if len(active_pool) > RESULTS_LIMIT:
            hint_parts.append("+ all")
        hint_parts += ["r remote", "p gates", "Enter skip"]
        print()
        try:
            sel = input(
                f"  {B}Assign stand{R} {DIM}({'  /  '.join(hint_parts)}):{R} "
            ).strip().upper()
        except (EOFError, KeyboardInterrupt):
            return

        if not sel:
            return

        # ── Re-filter modifiers ────────────────────────────────────────────────
        expand   = sel.endswith('+') or sel.startswith('+')
        core     = sel.replace('+', '').strip()

        if core in ('R', 'P', '') and (sel == '+' or core in ('R', 'P')):
            if core == 'R':
                new_pool = [p for p in all_pids if data_map[p].get('remote', False)]
                label    = "remote"
            elif core == 'P':
                new_pool = [p for p in all_pids if not data_map[p].get('remote', False)]
                label    = "gates"
            else:
                new_pool = list(all_pids)
                label    = "all"

            if not new_pool:
                print(f"  {YL}No stands match that filter.{R}")
                continue

            active_pool = new_pool
            print()
            _redisplay(active_pool, expand)
            continue

        # ── Stand ID ──────────────────────────────────────────────────────────
        if sel not in all_pids:
            print(f"  {YL}Stand '{sel}' not found — type + to see all options.{R}")
            continue

        data  = parkings.get(sel, {})
        excls = [ex for ex in data.get('excludes', []) if ex not in occupied]
        occupied.add(sel)
        for ex in data.get('excludes', []):
            occupied.add(ex)
        parts = [f"{GR}{B}{sel}{R}{GR} occupied{R}"]
        if excls:
            parts.append(f"{DIM}+ blocked: {', '.join(excls)}{R}")
        parts.append(f"{DIM}[{len(occupied)} unavailable this session]{R}")
        print("  " + "  ".join(parts))

        # ── Push gate label to Aurora ──────────────────────────────────────────
        if aurora and aurora.connected and callsign:
            ok, detail = aurora.assign_gate(callsign, sel)
            if ok:
                print(f"  {BL}Aurora: gate {B}{sel}{R}{BL} assigned to {callsign}{R}")
            else:
                print(f"  {YL}Aurora: gate label failed  {DIM}({detail}){R}")

        return


def run_query_ga(aircraft_type, wingspans, parkings, occupied):
    """GA mode: show stands 01-57 that fit the aircraft. Returns displayed pids."""
    wingspan = get_wingspan(aircraft_type, wingspans)

    print()
    _box_top("LEBL  PARKING  ASSIGNMENT")
    print()
    _info_row("Mode",     "General Aviation  (stands 01-57)")
    _info_row("Aircraft", f"{aircraft_type}  ·  {wingspan} m")

    candidates = {
        pid: data
        for pid, data in parkings.items()
        if data.get('schengen') == 'ga'
        and pid not in occupied
        and (data.get('max_wingspan') or 0) >= wingspan
    }

    if candidates:
        visible, all_pids = show_results("GA stands", list(candidates.keys()), candidates,
                                         schengen_flight=True, acft_ws=wingspan)
    else:
        _warn("No GA stand available for this aircraft.")
        visible, all_pids = [], []

    print()
    return visible, all_pids, candidates, True, wingspan


def run_query_cargo(aircraft_type, wingspans, parkings, occupied, airline_code=None):
    """Cargo mode: show stands 141-165 that fit the aircraft. Returns displayed pids."""
    wingspan = get_wingspan(aircraft_type, wingspans)

    print()
    _box_top("LEBL  PARKING  ASSIGNMENT")
    print()
    if airline_code:
        _info_row("Airline",  f"{airline_code}  ·  Cargo operator")
    _info_row("Mode",     "Cargo  (stands 141-165)")
    _info_row("Aircraft", f"{aircraft_type}  ·  {wingspan} m")

    candidates = {
        pid: data
        for pid, data in parkings.items()
        if data.get('schengen') == 'cargo'
        and pid not in occupied
        and (data.get('max_wingspan') or 999) >= wingspan
    }

    if candidates:
        visible, all_pids = show_results("Cargo stands", list(candidates.keys()), candidates,
                                         schengen_flight=True, acft_ws=wingspan)
    else:
        _warn("No cargo stand available for this aircraft.")
        visible, all_pids = [], []

    print()
    return visible, all_pids, candidates, True, wingspan


def run_query(airline_code, aircraft_type, origin,
              airlines, wingspans, parkings, occupied,
              force_remote=False, force_gate=False, force_schengen=None, force_terminal=None):
    """Run one parking lookup. Returns list of displayed stand IDs.

    force_remote    : if True, skip contact gates and show only remote stands
    force_schengen  : True=Schengen, False=Non-Schengen, None=auto-detect
    """

    # ── Wingspan ───────────────────────────────────────────────────────────────
    wingspan = get_wingspan(aircraft_type, wingspans)

    # ── Early cargo redirect (before any output) ───────────────────────────────
    if airline_code not in DEDICATED and get_airline_terminal(airlines, airline_code) == 'CARGO':
        return run_query_cargo(aircraft_type, wingspans, parkings, occupied,
                               airline_code=airline_code)

    # ── Schengen ───────────────────────────────────────────────────────────────
    if force_schengen is not None:
        sch_bool    = force_schengen
        sch_prefix  = origin[:2].upper() if origin and len(origin) >= 2 else '??'
    else:
        sch_bool, sch_prefix = is_schengen_flight(origin)
        if sch_bool is None:
            sch_bool = False
    sch_country = _country(sch_prefix)
    sch_str     = f"{GR}SCHENGEN{R}" if sch_bool else f"{RD}NON-SCHENGEN{R}"
    if force_schengen is not None:
        sch_str += f"  {DIM}(override){R}"

    # ── Remote flag label ──────────────────────────────────────────────────────
    remote_tag = f"  {YL}[remote only]{R}" if force_remote else (f"  {GR}[gates only]{R}" if force_gate else "")

    # ── Header ─────────────────────────────────────────────────────────────────
    print()
    _box_top("LEBL  PARKING  ASSIGNMENT")
    print()

    visible, all_pids, last_data_map = [], [], {}

    # Build tier list: one pool per terminal (gates+remotes merged so exact
    # wingspan matches always surface first regardless of gate/remote status).
    # force_remote filters within filter_parkings via the remote_only flag kept
    # only when explicitly requested.
    def make_tiers(terminal, other):
        if force_remote:
            return [
                (terminal, True,  f"{terminal} Remote stands"),
                (other,    True,  f"{other} Remote stands"),
            ]
        if force_gate:
            return [
                (terminal, False, f"{terminal} Contact gates"),
                (other,    False, f"{other} Contact gates (fallback)"),
            ]
        return [
            (terminal, None, f"{terminal}"),
            (other,    None, f"{other} (fallback)"),
        ]

    # ── Dedicated airline ──────────────────────────────────────────────────────
    if airline_code in DEDICATED:
        ded_terminal = DEDICATED_TERMINAL.get(airline_code, 'T1')
        ded_label    = DEDICATED_LABEL.get(airline_code, f"{airline_code} DEDICATED")
        other        = 'T2' if ded_terminal == 'T1' else 'T1'

        _info_row("Airline",  f"{airline_code}  ·  Terminal {ded_terminal} (dedicated){remote_tag}")
        _info_row("Aircraft", f"{aircraft_type}  ·  {wingspan} m")
        _info_row("Origin",   f"{origin}  ·  {sch_country}  ·  {sch_str}")

        dedicated = {
            pid: parkings[pid]
            for pid in DEDICATED[airline_code]
            if pid in parkings
            and pid not in occupied
            and (parkings[pid].get('max_wingspan') or 0) >= wingspan
            and schengen_ok(parkings[pid], sch_bool)
            and (not force_remote or parkings[pid].get('remote', False))
            and (not force_gate or not parkings[pid].get('remote', False))
        }

        if dedicated:
            visible, all_pids = show_results(ded_label, list(dedicated.keys()), dedicated,
                                             sch_bool, acft_ws=wingspan)
            last_data_map = dedicated
        else:
            _warn(f"No dedicated stand fits {aircraft_type} ({wingspan} m). Fallback:")
            for term, remote_only, lbl in make_tiers(ded_terminal, other):
                pool = filter_parkings(parkings, term, airline_code, wingspan, sch_bool, occupied)
                tier = [p for p in pool if remote_only is None or pool[p].get('remote', False) == remote_only]
                if tier:
                    dm = {p: pool[p] for p in tier}
                    visible, all_pids = show_results(lbl, tier, dm, sch_bool,
                                                     acft_ws=wingspan, is_fallback=True)
                    last_data_map = dm
                    break

    # ── Standard airline ───────────────────────────────────────────────────────
    else:
        terminal = get_airline_terminal(airlines, airline_code)
        if terminal is None:
            print(f"\n  {YL}Airline '{airline_code}' not in database.{R}")
            t = input("  Terminal (1/T1  2/T2  c/CARGO): ").strip().upper()
            terminal = {'1': 'T1', '2': 'T2', 'C': 'CARGO'}.get(t, t if t in ('T1', 'T2', 'CARGO') else 'T1')

        if force_terminal and terminal not in ('CARGO',):
            terminal = force_terminal
        if terminal == 'CARGO':
            return run_query_cargo(aircraft_type, wingspans, parkings, occupied,
                                   airline_code=airline_code)

        other = 'T2' if terminal == 'T1' else 'T1'

        _info_row("Airline",  f"{airline_code}  ·  Terminal {terminal}{remote_tag}")
        _info_row("Aircraft", f"{aircraft_type}  ·  {wingspan} m")
        _info_row("Origin",   f"{origin}  ·  {sch_country}  ·  {sch_str}")

        if wingspan >= WIDEBODY_THRESHOLD:
            _warn(f"{aircraft_type} ({wingspan} m) is a wide-body — limited stand options")

        shown = False
        for term, remote_only, lbl in make_tiers(terminal, other):
            pool = filter_parkings(parkings, term, airline_code, wingspan, sch_bool, occupied)
            tier = [p for p in pool if remote_only is None or pool[p].get('remote', False) == remote_only]
            if tier:
                dm = {p: pool[p] for p in tier}
                fallback = (term != terminal)
                visible, all_pids = show_results(lbl, tier, dm, sch_bool,
                                                 acft_ws=wingspan, is_fallback=fallback)
                last_data_map = dm
                shown = True
                break

        if not shown:
            _warn("No suitable parking positions found at LEBL.")

    print()
    return visible, all_pids, last_data_map, sch_bool, wingspan


# ─── Input parser ─────────────────────────────────────────────────────────────

def parse_input(raw):
    """
    Parse a raw query line into (mode, positional_args, flags).

    Modifier tokens (removed from positional list):
        r          → force_remote=True
        g          → ga_mode=True  (only aircraft type needed)
        s          → force_schengen=True
        ns         → force_schengen=False
        x <stand>  → release stand (handled before calling this)
        clear      → clear occupied (handled before calling this)
        ?          → print help

    Returns dict with keys:
        ga_mode, force_remote, force_schengen, positional (list)
    """
    MODIFIERS = {'R', 'G', 'S', 'NS'}
    tokens = raw.upper().split()
    flags      = {'ga_mode': False, 'cargo_mode': False, 'force_remote': False, 'force_gate': False, 'force_schengen': None, 'force_terminal': None}
    positional = []

    for tok in tokens:
        if tok == 'R':
            flags['force_remote'] = True
        elif tok == 'P':
            flags['force_gate'] = True
        elif tok == 'G':
            flags['ga_mode'] = True
        elif tok == 'C':
            flags['cargo_mode'] = True
        elif tok == 'S':
            flags['force_schengen'] = True
        elif tok == 'NS':
            flags['force_schengen'] = False
        elif tok in ('T1', 'T2'):
            flags['force_terminal'] = tok
        else:
            positional.append(tok)

    return flags, positional


HELP_TEXT = f"""
  {CY}{B}Query syntax (USE ICAO ONLY):{R}
    {WH}AIRLINE AIRCRAFT ORIGIN{R}        standard          (e.g. {DIM}VLG A320 LEPA{R})
    {WH}AIRCRAFT g{R}                     GA mode           (e.g. {DIM}C208 g{R})
    {WH}AIRCRAFT c{R}                     Cargo mode        (e.g. {DIM}B744 c{R})
    {WH}i STAND [AIRLINE ACFT ORIGIN]{R}  info & suitability(e.g. {DIM}i 258 VLG A320 LEPA{R})
    {WH}... r{R}                          force remote stands only
    {WH}... p{R}                          force contact gates only  (puerta)
    {WH}... s{R}  /  {WH}... ns{R}              override Schengen / Non-Schengen
    {WH}... t1{R} /  {WH}... t2{R}              override terminal

  {CY}{B}Stand management:{R}
    {WH}o STAND [STAND ...]{R}            occupy manually   (e.g. {DIM}o 242 243{R})
    {WH}x STAND [STAND ...]{R}            release stand     (e.g. {DIM}x 242{R})
    {WH}clear{R}                          release all occupied stands

  {CY}{B}Aurora (requires Aurora open + 3rd Party enabled):{R}
    {WH}a [CALLSIGN]{R}               auto-fetch FP from Aurora  (e.g. {DIM}a IBE1234{R})
                               omit callsign to use selected traffic
                               gate is pushed to Aurora after assignment

  {CY}{B}Other:{R}
    {WH}?{R}   help    {WH}q{R}   quit    {WH}cls{R}   clear screen (keeps occupied list)
  {DIM}Modifiers go anywhere: {R}{WH}AEA B738 r LFPO s{R}{DIM} is valid.{R}
"""


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    airlines  = load_json(AIRLINES_JSON,  "airlines.json")
    _build_dedicated(airlines)
    wingspans = load_json(WINGSPANS_JSON, "aircraft_wingspans.json")
    _build_suffix_map(wingspans)
    parkings  = load_json(PARKINGS_JSON,  "parkings.json")

    occupied: set = set()

    # ── Aurora connection (optional) ───────────────────────────────────────────
    aurora = AuroraBridge()
    if aurora.connect():
        print(f"  {GR}{B}Aurora connected{R}  {DIM}(localhost:1130){R}")
    else:
        print(f"  {YL}Aurora not available{R}  {DIM}(running without live data){R}")

    # ── One-shot CLI mode ──────────────────────────────────────────────────────
    args = sys.argv[1:]
    if args:
        flags, positional = parse_input(' '.join(args))
        if flags['ga_mode'] and positional:
            vis, all_p, dm, sch, aws = run_query_ga(resolve_aircraft_type(positional[0], wingspans), wingspans, parkings, occupied)
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)
            return
        if flags['cargo_mode'] and positional:
            vis, all_p, dm, sch, aws = run_query_cargo(resolve_aircraft_type(positional[0], wingspans), wingspans, parkings, occupied)
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)
            return
        if len(positional) >= 3:
            vis, all_p, dm, sch, aws = run_query(positional[0], resolve_aircraft_type(positional[1], wingspans), positional[2],
                                            airlines, wingspans, parkings, occupied,
                                            force_remote=flags['force_remote'],
                                            force_gate=flags['force_gate'],
                                            force_schengen=flags['force_schengen'],
                                            force_terminal=flags['force_terminal'])
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)
            return

    # ── Interactive session loop ───────────────────────────────────────────────
    aurora_status = f"{GR}Aurora{R}" if aurora.connected else f"{DIM}no Aurora{R}"
    print(f"\n{CY}{B}  LEBL Parking System{R}  {DIM}· '?' for help · 'q' to quit{R}  [{aurora_status}]")
    print(f"  {DIM}{'─' * 44}{R}")

    while True:
        # Show occupied summary
        if occupied:
            occ_sorted = sorted(occupied, key=lambda x: (get_numeric_id(x), x))
            print(f"\n  {DIM}Occupied: {', '.join(occ_sorted)}{R}")

        # Prompt
        print()
        try:
            raw = input(
                f"  {B}>{R} {DIM}Query (AIRLINE AIRCRAFT ORIGIN +flags):{R} "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{DIM}Session ended.{R}")
            break

        if not raw:
            continue
        raw_lower = raw.lower()

        # ── Special commands ───────────────────────────────────────────────────
        if raw_lower == 'q':
            print(f"{DIM}Session ended.{R}")
            break

        if raw_lower == '?':
            print(HELP_TEXT)
            continue

        # a [CALLSIGN] — fetch flight data from Aurora for selected/given callsign
        if raw_lower == 'a' or raw_lower.startswith('a '):
            if not aurora.connected:
                print(f"  {RD}Aurora not connected.{R}")
                continue
            parts = raw.upper().split()
            if len(parts) >= 2:
                cs = parts[1]
            else:
                cs = aurora.get_selected_callsign()
                if not cs:
                    print(f"  {YL}No traffic selected in Aurora.{R}")
                    continue
                print(f"  {DIM}Selected in Aurora: {WH}{B}{cs}{R}")
            fp = aurora.get_flight_plan(cs)
            if not fp:
                print(f"  {YL}No flight plan found for '{cs}' in Aurora.{R}")
                continue
            airline_code  = callsign_to_airline(cs)
            aircraft_type = resolve_aircraft_type(fp['aircraft'], wingspans) if fp['aircraft'] else None
            origin        = fp['departure'] if fp['departure'] else None
            if not airline_code:
                print(f"  {YL}Cannot extract airline code from '{cs}'.{R}")
                continue
            if not aircraft_type:
                print(f"  {YL}No aircraft type in flight plan for '{cs}'.{R}")
                continue
            if not origin:
                print(f"  {YL}No departure airport in flight plan for '{cs}'.{R}")
                continue
            print(f"  {DIM}Aurora FP: {WH}{cs}{R}  {DIM}→  {WH}{airline_code} {aircraft_type} from {origin}{R}")
            vis, all_p, dm, sch, aws = run_query(airline_code, aircraft_type, origin,
                                            airlines, wingspans, parkings, occupied)
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws,
                          aurora=aurora, callsign=cs)
            continue

        if raw_lower == 'clear':
            occupied.clear()
            print(f"  {GR}All stands released.{R}")
            continue

        if raw_lower in ('cls', 'reset'):
            import subprocess
            subprocess.run('cls', shell=True)
            print()
            print(f"{CY}{B}  LEBL Parking System{R}  {DIM}· '?' for help · 'q' to quit{R}")
            print(f'  {DIM}{chr(9472) * 44}{R}')
            continue

        # o <stand> — manually occupy stands
        if raw_lower.startswith('o ') or raw_lower == 'o':
            parts = raw.upper().split()
            if len(parts) >= 2:
                added = []
                for p in parts[1:]:
                    if p not in occupied:
                        occupied.add(p)
                        added.append(p)
                        # Also mark excludes of this stand
                        for ex in parkings.get(p, {}).get('excludes', []):
                            occupied.add(ex)
                if added:
                    print(f"  {YL}Occupied: {', '.join(added)}{R}  {DIM}[{len(occupied)} total]{R}")
                else:
                    print(f"  {DIM}Already in occupied list.{R}")
            else:
                print(f"  {YL}Usage: o STAND  (e.g. o 242){R}")
            continue

        # x <stand> — release stands
        if raw_lower.startswith('x ') or raw_lower == 'x':
            parts = raw.upper().split()
            if len(parts) >= 2:
                to_release = [p for p in parts[1:] if p in occupied]
                not_occ    = [p for p in parts[1:] if p not in occupied]
                for p in to_release:
                    occupied.discard(p)
                if to_release:
                    print(f"  {GR}Released: {', '.join(to_release)}{R}")
                if not_occ:
                    print(f"  {YL}Not in occupied list: {', '.join(not_occ)}{R}")
            else:
                print(f"  {YL}Usage: x STAND  (e.g. x 242){R}")
            continue

        # i <stand> [airline acft origin] — info about a stand
        if raw_lower.startswith('i ') or raw_lower == 'i':
            parts = raw.upper().split()
            if len(parts) >= 2:
                pid = parts[1]
                airline = parts[2] if len(parts) >= 3 else None
                acft = resolve_aircraft_type(parts[3], wingspans) if len(parts) >= 4 else None
                origin = parts[4] if len(parts) >= 5 else None
                info_stand(pid, parkings, occupied, airline, acft, origin, airlines, wingspans)
            else:
                print(f"  {YL}Usage: i STAND [AIRLINE ACFT ORIGIN]{R}")
            continue

        # ── Parse modifiers ────────────────────────────────────────────────────
        flags, positional = parse_input(raw)

        # GA mode
        if flags['ga_mode']:
            if not positional:
                print(f"  {YL}GA mode: enter aircraft type  (e.g. C208 g){R}")
                continue
            vis, all_p, dm, sch, aws = run_query_ga(resolve_aircraft_type(positional[0], wingspans), wingspans, parkings, occupied)
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)
            continue

        # Cargo mode
        if flags['cargo_mode']:
            if not positional:
                print(f"  {YL}Cargo mode: enter aircraft type  (e.g. B744 c){R}")
                continue
            vis, all_p, dm, sch, aws = run_query_cargo(resolve_aircraft_type(positional[0], wingspans), wingspans, parkings, occupied)
            assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)
            continue

        # Standard query
        if len(positional) < 3:
            print(f"  {YL}Need: AIRLINE AIRCRAFT ORIGIN  (modifiers: r s ns g){R}")
            continue

        airline_code  = positional[0]
        aircraft_type = resolve_aircraft_type(positional[1], wingspans)
        origin        = positional[2]

        vis, all_p, dm, sch, aws = run_query(airline_code, aircraft_type, origin,
                                        airlines, wingspans, parkings, occupied,
                                        force_remote=flags['force_remote'],
                                        force_gate=flags['force_gate'],
                                        force_schengen=flags['force_schengen'],
                                        force_terminal=flags['force_terminal'])
        assign_prompt(vis, all_p, dm, sch, parkings, occupied, acft_ws=aws, aurora=aurora)


if __name__ == "__main__":
    main()
