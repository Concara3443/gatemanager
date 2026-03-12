"""parking_gui.py
LEBL Parking Assignment — GUI interface.
Requires: tkinter (built-in), aurora_bridge.py, parking_finder.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import datetime
import json
import sys
import os

# Redirect uncaught errors to error.log (useful when launched via .vbs / pythonw)
_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')
sys.stderr = open(_LOG, 'a', encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from aurora_bridge import AuroraBridge, callsign_to_airline
import parking_finder as pf

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    'bg':       '#1a1a2e',
    'bg2':      '#16213e',
    'bg3':      '#0f0f23',
    'hdr':      '#0d0d1f',
    'sep':      '#4fc3f7',
    'accent':   '#4fc3f7',
    'green':    '#66bb6a',
    'orange':   '#ffa726',
    'red':      '#ef5350',
    'purple':   '#ce93d8',
    'fg':       '#e0e0e0',
    'fg_dim':   '#757575',
    'strip_bg': '#fffde7',
    'strip_sep':'#bdbdbd',
    'btn':      '#1c1c3a',
    'btn_hl':   '#2a2a50',
    'entry_bg': '#0d1b35',
}

FONT     = ('Consolas', 10)
FONT_SM  = ('Consolas', 9)
FONT_MED = ('Consolas', 11)
FONT_LG  = ('Consolas', 14, 'bold')
FONT_XL  = ('Consolas', 20, 'bold')


# ── App ───────────────────────────────────────────────────────────────────────

class ParkingApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("LEBL Parking Assignment  ·  v2.0")
        self.configure(bg=C['bg3'])
        self.minsize(960, 680)
        self.geometry('1060x730')

        # ── Data ──────────────────────────────────────────────────────────────
        self.airlines  = pf.load_json(pf.AIRLINES_JSON,  "airlines.json")
        pf._build_dedicated(self.airlines)
        self.wingspans = pf.load_json(pf.WINGSPANS_JSON, "aircraft_wingspans.json")
        pf._build_suffix_map(self.wingspans)
        self.parkings  = pf.load_json(pf.PARKINGS_JSON,  "parkings.json")

        # ── State ─────────────────────────────────────────────────────────────
        self.occupied       : set   = set()
        self.current_cs     : str   = ''
        self.current_dm     : dict  = {}
        self.all_sorted     : list  = []
        self.sch_bool       : bool  = True
        self.acft_ws        : float = 0.0
        self.selected_stand : str   = ''
        self._current_strip : dict  = {}

        # ── Auto-refresh ──────────────────────────────────────────────────────
        self._auto_var      = tk.BooleanVar(value=False)
        self._last_polled   : str   = ''   # last callsign seen in Aurora
        self._poll_job                = None
        POLL_MS             = 4000         # poll interval in ms

        # ── Aurora ────────────────────────────────────────────────────────────
        self.aurora = AuroraBridge()

        # ── Build UI ──────────────────────────────────────────────────────────
        self._build_ui()
        self._log("App started & initialized", 'info')
        self._try_connect_aurora()

        self.bind('<F5>', lambda e: self._query_aurora())
        self.bind('<Return>', lambda e: self._assign_stand())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.POLL_MS = 4000

    # ══════════════════════════════════════════════════════════════════════════
    # UI BUILD
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_header()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        self._build_body()
        tk.Frame(self, bg='#333', height=1).pack(fill=tk.X)
        self._build_log()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        self._build_buttons()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=C['hdr'], pady=10)
        hdr.pack(fill=tk.X)

        # Left: icon + title
        left = tk.Frame(hdr, bg=C['hdr'])
        left.pack(side=tk.LEFT, padx=14)

        tk.Label(left, text="✈", font=('Consolas', 28), bg=C['hdr'],
                 fg=C['accent']).pack(side=tk.LEFT)

        title_frame = tk.Frame(left, bg=C['hdr'])
        title_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(title_frame, text="LEBL Parking Assignment",
                 font=FONT_XL, bg=C['hdr'], fg=C['fg']).pack(anchor='w')
        tk.Label(title_frame, text="Barcelona El Prat  ·  IVAO Virtual ATC  ·  v2.0",
                 font=FONT_SM, bg=C['hdr'], fg=C['fg_dim']).pack(anchor='w')

        # Right: auto-refresh toggle + aurora status
        right = tk.Frame(hdr, bg=C['hdr'])
        right.pack(side=tk.RIGHT, padx=16)

        # Auto-refresh toggle
        self.auto_cb = tk.Checkbutton(
            right, text="Auto", font=FONT_SM,
            variable=self._auto_var,
            bg=C['hdr'], fg=C['fg_dim'],
            selectcolor=C['bg2'],
            activebackground=C['hdr'], activeforeground=C['fg'],
            command=self._on_auto_toggle)
        self.auto_cb.pack(side=tk.LEFT, padx=(0, 14))

        self.aurora_dot = tk.Label(right, text="●", font=('Consolas', 14),
                                   bg=C['hdr'], fg=C['red'])
        self.aurora_dot.pack(side=tk.LEFT)
        self.aurora_lbl = tk.Label(right, text="Aurora disconnected",
                                   font=FONT_SM, bg=C['hdr'], fg=C['red'])
        self.aurora_lbl.pack(side=tk.LEFT, padx=(4, 0))

    # ── Body (left panel + right table) ──────────────────────────────────────

    def _build_body(self):
        body = tk.Frame(self, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True)

        self._build_left_panel(body)
        tk.Frame(body, bg='#333', width=1).pack(side=tk.LEFT, fill=tk.Y)
        self._build_right_panel(body)

    def _build_left_panel(self, parent):
        left = tk.Frame(parent, bg=C['bg'], width=310)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        # ── Query inputs ──────────────────────────────────────────────────────
        self._section_label(left, "Query")
        inp = tk.Frame(left, bg=C['bg2'], padx=8, pady=6)
        inp.pack(fill=tk.X, padx=8, pady=(0, 6))

        self.v_callsign = tk.StringVar()
        self.v_airline  = tk.StringVar()
        self.v_aircraft = tk.StringVar()
        self.v_origin   = tk.StringVar()

        for label, var in [("Callsign", self.v_callsign),
                            ("Airline",  self.v_airline),
                            ("Aircraft", self.v_aircraft),
                            ("Origin",   self.v_origin)]:
            row = tk.Frame(inp, bg=C['bg2'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{label:<9}", font=FONT_SM,
                     bg=C['bg2'], fg=C['fg_dim'], width=9, anchor='w').pack(side=tk.LEFT)
            tk.Entry(row, textvariable=var, font=FONT,
                     bg=C['entry_bg'], fg=C['fg'], insertbackground=C['fg'],
                     relief=tk.FLAT, bd=4, width=14).pack(side=tk.LEFT, fill=tk.X,
                                                           expand=True)

        btn_row = tk.Frame(inp, bg=C['bg2'])
        btn_row.pack(fill=tk.X, pady=(6, 2))
        self._btn(btn_row, "Query  ▶", self._query_manual,
                  bg='#0d47a1').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        self._btn(btn_row, "Aurora  F5", self._query_aurora,
                  bg='#1b5e20').pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Strip card ────────────────────────────────────────────────────────
        self._section_label(left, "Current Strip")
        self.strip_outer = tk.Frame(left, bg=C['bg'], padx=8)
        self.strip_outer.pack(fill=tk.X)
        self.strip_frame = tk.Frame(self.strip_outer, bg=C['strip_bg'],
                                    bd=1, relief=tk.SOLID)
        self.strip_frame.pack(fill=tk.X)
        self._strip_empty()

        # ── Occupied ──────────────────────────────────────────────────────────
        self._section_label(left, "Occupied Stands")
        occ_outer = tk.Frame(left, bg=C['bg'], padx=8)
        occ_outer.pack(fill=tk.X)
        self.occ_label = tk.Label(occ_outer, text="—",
                                  font=FONT_SM, bg=C['bg2'], fg=C['orange'],
                                  anchor='nw', justify='left', wraplength=270,
                                  padx=6, pady=5)
        self.occ_label.pack(fill=tk.X)

        self._btn(occ_outer, "x  Release stand…", self._release_dialog,
                  bg='#1a1a1a').pack(fill=tk.X, pady=(3, 0))

    def _build_right_panel(self, parent):
        right = tk.Frame(parent, bg=C['bg'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._section_label(right, "Available Stands")

        # ── Table ──────────────────────────────────────────────────────────────
        style = ttk.Style(self)
        style.theme_use('default')
        style.configure('P.Treeview',
                         background=C['bg2'], fieldbackground=C['bg2'],
                         foreground=C['fg'], rowheight=24, font=FONT_SM,
                         borderwidth=0, relief='flat')
        style.configure('P.Treeview.Heading',
                         background=C['hdr'], foreground=C['accent'],
                         font=('Consolas', 9, 'bold'), relief='flat')
        style.map('P.Treeview',
                  background=[('selected', '#1565c0')],
                  foreground=[('selected', '#fff')])

        tbl_frame = tk.Frame(right, bg=C['bg'])
        tbl_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        cols = ('Stand', 'Max WS', 'Type', 'Zone', 'Notes')
        self.tree = ttk.Treeview(tbl_frame, columns=cols, show='headings',
                                  style='P.Treeview', selectmode='browse')
        widths = {'Stand': 66, 'Max WS': 68, 'Type': 64, 'Zone': 88, 'Notes': 200}
        for c in cols:
            self.tree.heading(c, text=c, anchor='w')
            self.tree.column(c, width=widths[c], anchor='w', minwidth=30)

        vsb = ttk.Scrollbar(tbl_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure('perfect', foreground=C['purple'])
        self.tree.tag_configure('gate',    foreground='#a5d6a7')
        self.tree.tag_configure('remote',  foreground=C['orange'])
        self.tree.tag_configure('fallbk',  foreground='#ffee58')

        self.tree.bind('<<TreeviewSelect>>', self._on_stand_select)
        self.tree.bind('<Double-1>', lambda e: self._assign_stand())

        # ── Assign button ──────────────────────────────────────────────────────
        self.assign_btn = tk.Button(
            right, text="Assign Stand  ↵",
            font=('Consolas', 10, 'bold'),
            bg='#1b5e20', fg='#fff', activebackground='#2e7d32',
            disabledforeground='#444', relief=tk.FLAT, cursor='hand2',
            padx=10, pady=7, state=tk.DISABLED,
            command=self._assign_stand)
        self.assign_btn.pack(fill=tk.X, padx=8, pady=(0, 6))

    # ── Log ───────────────────────────────────────────────────────────────────

    def _build_log(self):
        log_wrap = tk.Frame(self, bg=C['bg3'], height=130)
        log_wrap.pack(fill=tk.X)
        log_wrap.pack_propagate(False)

        tk.Label(log_wrap, text=" Log", font=FONT_SM,
                 bg=C['bg3'], fg=C['fg_dim'], anchor='w').pack(fill=tk.X, padx=8,
                                                                pady=(3, 0))
        self.log_box = tk.Text(log_wrap, bg=C['bg3'], fg=C['fg_dim'],
                               font=FONT_SM, relief=tk.FLAT,
                               state=tk.DISABLED, wrap=tk.WORD, height=5)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        for tag, col in [('info', C['accent']), ('ok', C['green']),
                          ('warn', C['orange']),  ('err', C['red'])]:
            self.log_box.tag_config(tag, foreground=col)

    # ── Bottom buttons ────────────────────────────────────────────────────────

    def _build_buttons(self):
        bar = tk.Frame(self, bg=C['hdr'], pady=7)
        bar.pack(fill=tk.X)

        self.conn_btn = self._btn(bar, "CONNECT TO AURORA", self._connect_aurora)
        self.conn_btn.pack(side=tk.LEFT, padx=(10, 4))

        self._btn(bar, "QUERY SELECTED  (F5)", self._query_aurora,
                  bg='#0a3d0a').pack(side=tk.LEFT, padx=4)
        self._btn(bar, "CLEAR ALL STANDS", self._clear_occupied,
                  bg='#3d0a0a').pack(side=tk.LEFT, padx=4)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _btn(self, parent, text, cmd, bg=None):
        bg = bg or C['btn']
        return tk.Button(parent, text=text, font=FONT_SM,
                         bg=bg, fg=C['fg'], activebackground=C['btn_hl'],
                         relief=tk.FLAT, cursor='hand2', padx=10, pady=5,
                         command=cmd)

    def _section_label(self, parent, text):
        tk.Label(parent, text=f"  {text}", font=FONT_SM,
                 bg=C['bg'], fg=C['fg_dim'], anchor='w').pack(
                     fill=tk.X, pady=(8, 2))

    # ══════════════════════════════════════════════════════════════════════════
    # STRIP CARD
    # ══════════════════════════════════════════════════════════════════════════

    def _strip_empty(self):
        for w in self.strip_frame.winfo_children():
            w.destroy()
        tk.Label(self.strip_frame, text="No assignment yet",
                 font=FONT_SM, bg=C['strip_bg'], fg='#999',
                 pady=18, padx=10).pack()

    def _strip_update(self, callsign, airline, aircraft, origin,
                      stand, sch_str, terminal):
        for w in self.strip_frame.winfo_children():
            w.destroy()
        f = self.strip_frame

        # ── Row 1: callsign + aircraft + terminal badge ────────────────────────
        r1 = tk.Frame(f, bg=C['strip_bg'])
        r1.pack(fill=tk.X)

        tk.Label(r1, text=callsign or '—', font=FONT_LG,
                 bg=C['strip_bg'], fg='#000', padx=6, pady=3).pack(side=tk.LEFT)
        tk.Label(r1, text=aircraft, font=('Consolas', 11),
                 bg=C['strip_bg'], fg='#333').pack(side=tk.LEFT, padx=6)

        t_bg = '#0d47a1' if terminal in ('T1',) else \
               '#880e4f' if terminal == 'T2' else '#4e342e'
        tk.Label(r1, text=f" {terminal} ",
                 font=('Consolas', 9, 'bold'),
                 bg=t_bg, fg='#fff').pack(side=tk.RIGHT, padx=5, pady=3)

        tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)

        # ── Row 2: airline + origin + schengen badge ──────────────────────────
        r2 = tk.Frame(f, bg=C['strip_bg'])
        r2.pack(fill=tk.X)

        tk.Label(r2, text=airline, font=FONT_SM,
                 bg=C['strip_bg'], fg='#444', padx=6, pady=2).pack(side=tk.LEFT)
        tk.Label(r2, text=origin, font=('Consolas', 9, 'bold'),
                 bg=C['strip_bg'], fg='#000').pack(side=tk.LEFT, padx=4)

        is_sch = 'NON' not in sch_str.upper()
        s_bg   = '#1b5e20' if is_sch else '#b71c1c'
        tk.Label(r2, text=f"  {sch_str}  ", font=('Consolas', 8),
                 bg=s_bg, fg='#fff', pady=2).pack(side=tk.LEFT, padx=4)

        tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)

        # ── Row 3: assigned stand ─────────────────────────────────────────────
        r3 = tk.Frame(f, bg='#111')
        r3.pack(fill=tk.X)

        if stand:
            tk.Label(r3, text=f"  STAND  {stand}  ",
                     font=('Consolas', 16, 'bold'),
                     bg='#111', fg='#ffffff', pady=5).pack(side=tk.LEFT)
            tk.Label(r3, text="ASSIGNED", font=('Consolas', 8),
                     bg='#111', fg=C['green']).pack(side=tk.LEFT, padx=4)
        else:
            tk.Label(r3, text="  STAND  —  PENDING",
                     font=('Consolas', 12),
                     bg='#111', fg='#555', pady=5).pack()

    # ══════════════════════════════════════════════════════════════════════════
    # AURORA
    # ══════════════════════════════════════════════════════════════════════════

    def _try_connect_aurora(self):
        def _do():
            if self.aurora.connect():
                self.after(0, self._on_aurora_ok)
            else:
                self.after(0, self._on_aurora_fail)
        threading.Thread(target=_do, daemon=True).start()

    def _connect_aurora(self):
        self.aurora.disconnect()
        self.aurora_dot.config(fg=C['orange'])
        self.aurora_lbl.config(text="Connecting…", fg=C['orange'])
        self._try_connect_aurora()

    def _on_aurora_ok(self):
        self.aurora_dot.config(fg=C['green'])
        self.aurora_lbl.config(text="Aurora connected", fg=C['green'])
        self.conn_btn.config(text="RECONNECT AURORA")
        self._log("Connected to Aurora  (localhost:1130)", 'ok')
        if self._auto_var.get():
            self._poll()

    def _on_aurora_fail(self):
        self.aurora_dot.config(fg=C['red'])
        self.aurora_lbl.config(text="Aurora disconnected", fg=C['red'])
        self._log("Aurora not available — running standalone", 'warn')

    # ══════════════════════════════════════════════════════════════════════════
    # QUERY
    # ══════════════════════════════════════════════════════════════════════════

    def _query_aurora(self):
        if not self.aurora.connected:
            self._log("Aurora not connected", 'warn')
            return
        cs = self.aurora.get_selected_callsign()
        if not cs:
            self._log("No traffic selected in Aurora", 'warn')
            return
        fp = self.aurora.get_flight_plan(cs)
        if not fp:
            self._log(f"No flight plan for {cs}", 'warn')
            return

        airline  = callsign_to_airline(cs) or ''
        aircraft = fp.get('aircraft', '')
        origin   = fp.get('departure', '')

        self.v_callsign.set(cs)
        self.v_airline.set(airline)
        self.v_aircraft.set(aircraft)
        self.v_origin.set(origin)

        self._log(f"Aurora FP: {cs} → {airline} {aircraft} from {origin}", 'info')
        self._run_query(cs, airline, aircraft, origin)

    def _query_manual(self):
        cs      = self.v_callsign.get().strip().upper()
        airline = self.v_airline.get().strip().upper()
        acft    = self.v_aircraft.get().strip().upper()
        origin  = self.v_origin.get().strip().upper()

        if not airline or not acft or not origin:
            messagebox.showwarning("Missing fields",
                "Fill in at least Airline, Aircraft, and Origin.", parent=self)
            return
        self._run_query(cs or None, airline, acft, origin)

    def _run_query(self, callsign, airline_code, aircraft_type, origin):
        self.current_cs     = callsign or ''
        self.selected_stand = ''
        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵")

        # ── Wingspan ──────────────────────────────────────────────────────────
        aircraft_type = pf.resolve_aircraft_type(aircraft_type, self.wingspans)
        ws = self.wingspans.get(aircraft_type)
        if ws is None:
            ws = simpledialog.askfloat(
                "Unknown Aircraft",
                f"'{aircraft_type}' not in database.\nWingspan in metres:",
                parent=self, minvalue=5.0, maxvalue=110.0)
            if ws:
                self.wingspans[aircraft_type] = ws
                try:
                    sw = dict(sorted(self.wingspans.items()))
                    with open(pf.WINGSPANS_JSON, 'w', encoding='utf-8') as fh:
                        json.dump(sw, fh, indent=2)
                except Exception:
                    pass
            ws = ws or 36.0
        self.acft_ws = ws

        # ── Schengen ──────────────────────────────────────────────────────────
        prefix = origin[:2].upper() if len(origin) >= 2 else ''
        if prefix in pf.SCHENGEN_PREFIXES:
            sch = True
        elif prefix in pf.NON_SCHENGEN_PREFIXES:
            sch = False
        else:
            sch = messagebox.askyesno(
                "Schengen?",
                f"Unknown prefix '{prefix}' ({origin}).\nIs this a Schengen flight?",
                parent=self)
        self.sch_bool = sch
        sch_str = "SCHENGEN" if sch else "NON-SCHENGEN"
        country = pf._country(prefix)

        # ── Terminal / dedicated / cargo ──────────────────────────────────────
        terminal = pf.get_airline_terminal(self.airlines, airline_code)

        # Cargo
        if terminal == 'CARGO':
            pool = {
                pid: d for pid, d in self.parkings.items()
                if d.get('schengen') == 'cargo'
                and pid not in self.occupied
                and (d.get('max_wingspan') or 999) >= ws
            }
            self._populate_table(pool, sch, ws, fallback=False)
            self.current_dm = pool
            self._strip_update(callsign or airline_code, airline_code,
                               aircraft_type, origin, '', sch_str, 'CARGO')
            self._log(f"CARGO  {airline_code} {aircraft_type} — {len(pool)} stands", 'info')
            return

        # Dedicated
        if airline_code in pf.DEDICATED:
            ded_term = pf.DEDICATED_TERMINAL.get(airline_code, 'T1')
            other    = 'T2' if ded_term == 'T1' else 'T1'
            dedicated = {
                pid: self.parkings[pid]
                for pid in pf.DEDICATED[airline_code]
                if pid in self.parkings
                and pid not in self.occupied
                and (self.parkings[pid].get('max_wingspan') or 0) >= ws
                and pf.schengen_ok(self.parkings[pid], sch)
            }
            if dedicated:
                self._populate_table(dedicated, sch, ws, fallback=False)
                self.current_dm = dedicated
                self._log(f"Dedicated {airline_code}: {len(dedicated)} stands", 'info')
            else:
                pool = pf.filter_parkings(self.parkings, ded_term,
                                          airline_code, ws, sch, self.occupied)
                if not pool:
                    pool = pf.filter_parkings(self.parkings, other,
                                              airline_code, ws, sch, self.occupied)
                self._populate_table(pool, sch, ws, fallback=True)
                self.current_dm = pool
                self._log(f"No dedicated stand — fallback: {len(pool)} stands", 'warn')
            terminal = ded_term

        # Standard
        else:
            if terminal is None:
                ans = simpledialog.askstring(
                    "Unknown Airline",
                    f"'{airline_code}' not in database.\nTerminal (T1 / T2 / CARGO):",
                    parent=self)
                terminal = (ans or 'T1').strip().upper()
                self.airlines[airline_code] = terminal

            if terminal == 'CARGO':
                self._run_query(callsign, airline_code, aircraft_type, origin)
                return

            other    = 'T2' if terminal == 'T1' else 'T1'
            pool     = pf.filter_parkings(self.parkings, terminal,
                                          airline_code, ws, sch, self.occupied)
            fallback = False
            if not pool:
                pool     = pf.filter_parkings(self.parkings, other,
                                              airline_code, ws, sch, self.occupied)
                fallback = True
            self._populate_table(pool, sch, ws, fallback=fallback)
            self.current_dm = pool
            fb = "FALLBACK  " if fallback else ""
            self._log(
                f"{fb}{airline_code} {aircraft_type} {origin}  ({sch_str}, {country})"
                f"  →  {len(pool)} stands", 'warn' if fallback else 'info')

        self._strip_update(callsign or airline_code, airline_code,
                           aircraft_type, origin, '', sch_str, terminal or 'T1')

    def _populate_table(self, data_map, sch, acft_ws, fallback=False):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_sorted = []
        if not data_map:
            return

        prefer = 'schengen_only' if sch else 'non_schengen_only'
        self.all_sorted = sorted(
            data_map.keys(),
            key=lambda p: pf._sort_key(p, data_map[p], prefer, sch))

        for pid in self.all_sorted:
            d      = data_map[pid]
            ws     = d.get('max_wingspan')
            remote = d.get('remote', False)
            excl   = d.get('excludes', [])
            stype  = d.get('schengen', 'mixed')
            fit    = ws is not None and ws == acft_ws

            ws_s   = (f"{ws} m ★" if fit else f"{ws} m") if ws is not None else "?"
            notes  = ', '.join(excl) if excl else '—'
            zone   = pf.SCHENGEN_LABELS.get(stype, stype)

            tag = 'perfect' if fit else ('fallbk' if fallback else
                                          ('remote' if remote else 'gate'))
            self.tree.insert('', 'end', iid=pid,
                              values=(pid, ws_s, 'Remote' if remote else 'Gate',
                                      zone, notes),
                              tags=(tag,))

        # Auto-select best
        if self.all_sorted:
            self.tree.selection_set(self.all_sorted[0])
            self.tree.focus(self.all_sorted[0])
            self.tree.see(self.all_sorted[0])

    def _on_stand_select(self, _event=None):
        sel = self.tree.selection()
        if sel:
            self.selected_stand = sel[0]
            self.assign_btn.config(
                state=tk.NORMAL,
                text=f"Assign Stand  {self.selected_stand}  ↵")

    # ══════════════════════════════════════════════════════════════════════════
    # ASSIGN
    # ══════════════════════════════════════════════════════════════════════════

    def _assign_stand(self):
        if not self.selected_stand:
            return
        stand = self.selected_stand
        data  = self.parkings.get(stand, {})
        excls = [ex for ex in data.get('excludes', []) if ex not in self.occupied]

        self.occupied.add(stand)
        for ex in data.get('excludes', []):
            self.occupied.add(ex)

        # Update strip
        cs      = self.current_cs or self.v_callsign.get().strip().upper() or '—'
        airline = self.v_airline.get().strip().upper()
        acft    = self.v_aircraft.get().strip().upper()
        origin  = self.v_origin.get().strip().upper()
        sch_str = "SCHENGEN" if self.sch_bool else "NON-SCHENGEN"
        term    = pf.get_airline_terminal(self.airlines, airline) or \
                  self.parkings.get(stand, {}).get('terminal', 'T1')
        self._strip_update(cs, airline, acft, origin, stand, sch_str, term)

        # Remove assigned + blocked from table
        to_del = {stand} | set(data.get('excludes', []))
        for item in list(self.tree.get_children()):
            if item in to_del:
                self.tree.delete(item)

        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵")
        self.selected_stand = ''
        self._update_occupied()

        blocked = f"  (blocked: {', '.join(excls)})" if excls else ""
        self._log(f"[OK]  {cs} → Stand {stand}{blocked}", 'ok')

        # Push to Aurora
        if self.aurora.connected and self.current_cs:
            ok, detail = self.aurora.assign_gate(self.current_cs, stand)
            if ok:
                self._log(f"Aurora: #{self.current_cs} gate {stand} set", 'ok')
            else:
                self._log(f"Aurora gate label: {detail}", 'warn')

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _update_occupied(self):
        if self.occupied:
            occ = sorted(self.occupied,
                         key=lambda x: (pf.get_numeric_id(x), x))
            self.occ_label.config(text='  '.join(occ))
        else:
            self.occ_label.config(text='—')

    def _clear_occupied(self):
        self.occupied.clear()
        self._update_occupied()
        self._log("All stands cleared", 'info')

    def _release_dialog(self):
        stand = simpledialog.askstring("Release Stand",
                                       "Stand ID to release:", parent=self)
        if not stand:
            return
        stand = stand.strip().upper()
        if stand in self.occupied:
            self.occupied.discard(stand)
            self._update_occupied()
            self._log(f"Released: {stand}", 'info')
        else:
            self._log(f"Stand {stand} not in occupied list", 'warn')

    def _log(self, msg, level='info'):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"{ts}  {msg}\n", level)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ══════════════════════════════════════════════════════════════════════════
    # AUTO-REFRESH
    # ══════════════════════════════════════════════════════════════════════════

    def _on_auto_toggle(self):
        if self._auto_var.get():
            if not self.aurora.connected:
                self._log("Auto-refresh requires Aurora connection", 'warn')
                self._auto_var.set(False)
                return
            self.auto_cb.config(fg=C['green'])
            self._log(f"Auto-refresh ON  (every {self.POLL_MS // 1000}s)", 'info')
            self._poll()
        else:
            self.auto_cb.config(fg=C['fg_dim'])
            self._stop_poll()
            self._log("Auto-refresh OFF", 'info')

    def _poll(self):
        """Poll Aurora for selected callsign; re-query if it changed."""
        if not self._auto_var.get() or not self.aurora.connected:
            return

        def _do():
            cs = self.aurora.get_selected_callsign()
            self.after(0, lambda: self._handle_poll(cs))

        threading.Thread(target=_do, daemon=True).start()
        self._poll_job = self.after(self.POLL_MS, self._poll)

    def _handle_poll(self, cs):
        if not cs or cs == self._last_polled:
            return
        self._last_polled = cs
        fp = self.aurora.get_flight_plan(cs)
        if not fp:
            return
        airline  = callsign_to_airline(cs) or ''
        aircraft = fp.get('aircraft', '')
        origin   = fp.get('departure', '')
        if not airline or not aircraft or not origin:
            return
        self.v_callsign.set(cs)
        self.v_airline.set(airline)
        self.v_aircraft.set(aircraft)
        self.v_origin.set(origin)
        self._log(f"Auto: {cs} → {airline} {aircraft} from {origin}", 'info')
        self._run_query(cs, airline, aircraft, origin)

    def _stop_poll(self):
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None

    def _on_close(self):
        self._stop_poll()
        self.aurora.disconnect()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = ParkingApp()
    app.mainloop()
