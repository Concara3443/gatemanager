"""parking_gui.py — LEBL Parking Assignment GUI  v2.1"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading, datetime, json, sys, os

_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'error.log')
_log_fh = open(_LOG, 'a', encoding='utf-8')
sys.stderr = _log_fh

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from aurora_bridge import AuroraBridge, callsign_to_airline
import parking_finder as pf

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    'bg':       '#1a1a2e', 'bg2':  '#16213e', 'bg3':  '#0f0f23',
    'hdr':      '#0d0d1f', 'sep':  '#4fc3f7', 'accent':'#4fc3f7',
    'green':    '#66bb6a', 'orange':'#ffa726', 'red':  '#ef5350',
    'purple':   '#ce93d8', 'fg':   '#e0e0e0', 'fg_dim':'#757575',
    'strip_bg': '#fffde7', 'strip_sep':'#bdbdbd',
    'btn':      '#1c1c3a', 'btn_hl':'#2a2a50', 'entry_bg':'#0d1b35',
    'seg_on':   '#1565c0', 'seg_off':'#111122',
}
FONT   = ('Consolas', 10)
FONT_S = ('Consolas', 9)
FONT_L = ('Consolas', 14, 'bold')
FONT_X = ('Consolas', 20, 'bold')


# ── Helpers ───────────────────────────────────────────────────────────────────

def _btn(parent, text, cmd, bg=None, fg=None, **kw):
    return tk.Button(parent, text=text, font=FONT_S,
                     bg=bg or C['btn'], fg=fg or C['fg'],
                     activebackground=C['btn_hl'], relief=tk.FLAT,
                     cursor='hand2', padx=10, pady=5, command=cmd, **kw)


class SegGroup:
    """Row of flat toggle buttons — only one active at a time."""
    def __init__(self, parent, options, default, on_change=None):
        self.var = tk.StringVar(value=default)
        self._btns = {}
        self._cb = on_change
        for val, lbl in options:
            b = tk.Button(parent, text=lbl, font=FONT_S,
                          relief=tk.FLAT, cursor='hand2', padx=8, pady=3,
                          command=lambda v=val: self._pick(v))
            b.pack(side=tk.LEFT, padx=1)
            self._btns[val] = b
        self._refresh()

    def _pick(self, val):
        self.var.set(val)
        self._refresh()
        if self._cb:
            self._cb(val)

    def _refresh(self):
        cur = self.var.get()
        for val, b in self._btns.items():
            on = val == cur
            b.config(bg=C['seg_on'] if on else C['seg_off'],
                     fg=C['fg']     if on else C['fg_dim'])

    def get(self):
        return self.var.get()


# ── Main App ──────────────────────────────────────────────────────────────────

class ParkingApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("LEBL Parking Assignment  ·  v2.1")
        self.configure(bg=C['bg3'])
        self.minsize(1020, 700)
        self.geometry('1120x760')

        # Data
        self.airlines  = pf.load_json(pf.AIRLINES_JSON,  "airlines.json")
        pf._build_dedicated(self.airlines)
        self.wingspans = pf.load_json(pf.WINGSPANS_JSON, "aircraft_wingspans.json")
        pf._build_suffix_map(self.wingspans)
        self.parkings  = pf.load_json(pf.PARKINGS_JSON,  "parkings.json")

        # State
        self.occupied       : set   = set()
        self.occupied_by    : dict  = {}   # {stand: {'cs','acft','airline'}}
        self.current_cs     : str   = ''
        self.current_dm     : dict  = {}
        self.all_sorted     : list  = []
        self.sch_bool       : bool  = True
        self.acft_ws        : float = 0.0
        self.selected_stand : str   = ''
        self.preassigned    : dict  = {}   # {cs: {stand,airline,aircraft,origin,time}}
        self.assignments    : list  = []   # history of all assignments
        self._assign_win             = None
        self._occ_win                = None
        self._my_callsign   : str   = ''   # our ATC callsign in Aurora

        # Auto-refresh
        self._auto_var    = tk.BooleanVar(value=False)
        self._last_polled : str  = ''
        self._poll_job          = None
        self.POLL_MS      = 4000

        # Aurora
        self.aurora = AuroraBridge()

        self._build_ui()
        self._log("App started & initialized", 'info')
        self._try_connect_aurora()

        self.bind('<F5>', lambda e: self._query_aurora())
        self.bind('<Return>', lambda e: self._assign_stand())
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════════════════════════════════════════
    # BUILD UI
    # ══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        self._build_header()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        body = tk.Frame(self, bg=C['bg'])
        body.pack(fill=tk.BOTH, expand=True)
        self._build_left(body)
        tk.Frame(body, bg='#2a2a2a', width=1).pack(side=tk.LEFT, fill=tk.Y)
        self._build_right(body)
        tk.Frame(self, bg='#2a2a2a', height=1).pack(fill=tk.X)
        self._build_log()
        tk.Frame(self, bg=C['sep'], height=2).pack(fill=tk.X)
        self._build_footer()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=C['hdr'], pady=10)
        hdr.pack(fill=tk.X)

        lf = tk.Frame(hdr, bg=C['hdr'])
        lf.pack(side=tk.LEFT, padx=14)
        tk.Label(lf, text="✈", font=('Consolas', 28), bg=C['hdr'],
                 fg=C['accent']).pack(side=tk.LEFT)
        tf = tk.Frame(lf, bg=C['hdr'])
        tf.pack(side=tk.LEFT, padx=10)
        tk.Label(tf, text="LEBL Parking Assignment",
                 font=FONT_X, bg=C['hdr'], fg=C['fg']).pack(anchor='w')
        tk.Label(tf, text="Barcelona El Prat  ·  IVAO Virtual ATC  ·  v2.1",
                 font=FONT_S, bg=C['hdr'], fg=C['fg_dim']).pack(anchor='w')

        rf = tk.Frame(hdr, bg=C['hdr'])
        rf.pack(side=tk.RIGHT, padx=16)

        self.auto_cb = tk.Checkbutton(
            rf, text="Auto", font=FONT_S, variable=self._auto_var,
            bg=C['hdr'], fg=C['fg_dim'], selectcolor=C['bg2'],
            activebackground=C['hdr'], activeforeground=C['fg'],
            command=self._on_auto_toggle)
        self.auto_cb.pack(side=tk.LEFT, padx=(0, 16))

        self.aurora_dot = tk.Label(rf, text="●", font=('Consolas', 14),
                                   bg=C['hdr'], fg=C['red'])
        self.aurora_dot.pack(side=tk.LEFT)
        self.aurora_lbl = tk.Label(rf, text="Aurora disconnected",
                                   font=FONT_S, bg=C['hdr'], fg=C['red'])
        self.aurora_lbl.pack(side=tk.LEFT, padx=(4, 0))

    # ── Left panel ────────────────────────────────────────────────────────────

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=C['bg'], width=320)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        # ── Inputs ────────────────────────────────────────────────────────────
        self._slabel(left, "Query  (1, 2 o 3 campos)")
        inp = tk.Frame(left, bg=C['bg2'], padx=8, pady=6)
        inp.pack(fill=tk.X, padx=8, pady=(0, 2))

        self.v_callsign = tk.StringVar()
        self.v_airline  = tk.StringVar()
        self.v_aircraft = tk.StringVar()
        self.v_origin   = tk.StringVar()

        fields = [("Callsign", self.v_callsign, ""),
                  ("Airline",  self.v_airline,  "opcional"),
                  ("Aircraft", self.v_aircraft, "opcional"),
                  ("Origin",   self.v_origin,   "opcional")]

        for lbl, var, hint in fields:
            row = tk.Frame(inp, bg=C['bg2'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{lbl:<9}", font=FONT_S,
                     bg=C['bg2'], fg=C['fg_dim'], width=9,
                     anchor='w').pack(side=tk.LEFT)
            tk.Entry(row, textvariable=var, font=FONT,
                     bg=C['entry_bg'], fg=C['fg'],
                     insertbackground=C['fg'],
                     relief=tk.FLAT, bd=4, width=13).pack(
                         side=tk.LEFT, fill=tk.X, expand=True)
            if hint:
                tk.Label(row, text=hint, font=('Consolas', 8),
                         bg=C['bg2'], fg=C['fg_dim']).pack(side=tk.LEFT, padx=3)

        # ── Filters ───────────────────────────────────────────────────────────
        self._slabel(left, "Filtros")
        flt = tk.Frame(left, bg=C['bg2'], padx=8, pady=6)
        flt.pack(fill=tk.X, padx=8, pady=(0, 2))

        filter_rows = [
            ("Tipo",     [('all','Todo'), ('gates','Gates'), ('remote','Remote')]),
            ("Schengen", [('auto','Auto'), ('yes','SCH'), ('no','No-SCH')]),
            ("Terminal", [('auto','Auto'), ('T1','T1'), ('T2','T2')]),
        ]
        self.seg = {}
        for label, opts in filter_rows:
            row = tk.Frame(flt, bg=C['bg2'])
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{label:<9}", font=FONT_S, bg=C['bg2'],
                     fg=C['fg_dim'], width=9, anchor='w').pack(side=tk.LEFT)
            seg_frame = tk.Frame(row, bg=C['bg2'])
            seg_frame.pack(side=tk.LEFT)
            self.seg[label] = SegGroup(seg_frame, opts, opts[0][0])

        # Query buttons
        brow = tk.Frame(inp, bg=C['bg2'])
        brow.pack(fill=tk.X, pady=(6, 2))
        _btn(brow, "Query  ▶", self._query_manual,
             bg='#0d47a1').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        _btn(brow, "Aurora  F5", self._query_aurora,
             bg='#1b5e20').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
        _btn(brow, "✕", self._clear_query,
             bg='#2a1010', fg=C['red']).pack(side=tk.LEFT)

        # ── Strip card ────────────────────────────────────────────────────────
        self._slabel(left, "Current Strip")
        sf = tk.Frame(left, bg=C['bg'], padx=8)
        sf.pack(fill=tk.X)
        self.strip_frame = tk.Frame(sf, bg=C['strip_bg'], bd=1, relief=tk.SOLID)
        self.strip_frame.pack(fill=tk.X)
        self._strip_empty()

        # ── Occupied ──────────────────────────────────────────────────────────
        self._slabel(left, "Stands ocupados")
        of = tk.Frame(left, bg=C['bg'], padx=8)
        of.pack(fill=tk.X)
        self.occ_label = tk.Label(of, text="—", font=FONT_S, bg=C['bg2'],
                                  fg=C['orange'], anchor='nw', justify='left',
                                  wraplength=280, padx=6, pady=5)
        self.occ_label.pack(fill=tk.X)
        occ_btns = tk.Frame(of, bg=C['bg'])
        occ_btns.pack(fill=tk.X, pady=(3, 0))
        _btn(occ_btns, "⟳  Sync Aurora", self._sync_occupied_aurora,
             bg='#0a2a1a').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
        _btn(occ_btns, "▦  Ver ocupados", self._open_occupied_panel,
             bg='#1a2a3a').pack(side=tk.LEFT, fill=tk.X, expand=True)
        _btn(of, "x  Liberar stand…", self._release_dialog,
             bg='#1a1a1a').pack(fill=tk.X, pady=(2, 0))

    # ── Right panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=C['bg'])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._slabel(right, "Stands disponibles")

        # Table
        style = ttk.Style(self)
        style.theme_use('default')
        style.configure('P.Treeview',
                         background=C['bg2'], fieldbackground=C['bg2'],
                         foreground=C['fg'], rowheight=24, font=FONT_S,
                         borderwidth=0, relief='flat')
        style.configure('P.Treeview.Heading',
                         background=C['hdr'], foreground=C['accent'],
                         font=('Consolas', 9, 'bold'), relief='flat')
        style.map('P.Treeview',
                  background=[('selected', '#1565c0')],
                  foreground=[('selected', '#fff')])

        tf = tk.Frame(right, bg=C['bg'])
        tf.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))

        cols = ('Stand', 'Max WS', 'Tipo', 'Zona', 'Max Acft', 'Excluye')
        self.tree = ttk.Treeview(tf, columns=cols, show='headings',
                                  style='P.Treeview', selectmode='browse')
        cw = {'Stand':62,'Max WS':68,'Tipo':62,'Zona':88,'Max Acft':72,'Excluye':180}
        for c in cols:
            self.tree.heading(c, text=c, anchor='w')
            self.tree.column(c, width=cw[c], anchor='w', minwidth=30)

        vsb = ttk.Scrollbar(tf, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

        self.tree.tag_configure('perfect', foreground=C['purple'])
        self.tree.tag_configure('gate',    foreground='#a5d6a7')
        self.tree.tag_configure('remote',  foreground=C['orange'])
        self.tree.tag_configure('fallbk',  foreground='#ffee58')

        self.tree.bind('<<TreeviewSelect>>', self._on_stand_select)
        self.tree.bind('<Double-1>', lambda e: self._assign_stand())

        # ── Stand info box ────────────────────────────────────────────────────
        # Search bar
        sh = tk.Frame(right, bg=C['bg'])
        sh.pack(fill=tk.X, padx=8, pady=(0, 2))
        tk.Label(sh, text="  Info stand", font=FONT_S,
                 bg=C['bg'], fg=C['fg_dim']).pack(side=tk.LEFT)
        self.v_stand_search = tk.StringVar()
        se = tk.Entry(sh, textvariable=self.v_stand_search, font=FONT,
                      bg=C['entry_bg'], fg=C['fg'], insertbackground=C['fg'],
                      relief=tk.FLAT, bd=4, width=8)
        se.pack(side=tk.LEFT, padx=(8, 3))
        se.bind('<Return>', lambda e: self._lookup_stand())
        _btn(sh, "Buscar ▶", self._lookup_stand,
             bg='#1c2a4a').pack(side=tk.LEFT)

        info_outer = tk.Frame(right, bg=C['bg2'], padx=10, pady=6)
        info_outer.pack(fill=tk.X, padx=8, pady=(0, 4))

        self._info_lbl = {}
        info_fields = [
            ('Stand',    'Stand'),
            ('Terminal', 'Terminal'),
            ('Tipo',     'Tipo'),
            ('Max WS',   'Max WS'),
            ('Max Acft', 'Max Acft'),
            ('Zona',     'Zona'),
            ('Excluye',  'Excluye'),
            ('Estado',   'Estado'),
        ]
        grid = tk.Frame(info_outer, bg=C['bg2'])
        grid.pack(fill=tk.X)
        col_a = tk.Frame(grid, bg=C['bg2'])
        col_a.pack(side=tk.LEFT, fill=tk.X, expand=True)
        col_b = tk.Frame(grid, bg=C['bg2'])
        col_b.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pairs = [info_fields[i:i+2] for i in range(0, len(info_fields), 2)]
        for (ka, la), (kb, lb) in pairs:
            for col, key, label in [(col_a, ka, la), (col_b, kb, lb)]:
                r = tk.Frame(col, bg=C['bg2'])
                r.pack(fill=tk.X, pady=1)
                tk.Label(r, text=f"{label}:", font=FONT_S,
                         bg=C['bg2'], fg=C['fg_dim'],
                         width=9, anchor='w').pack(side=tk.LEFT)
                v = tk.Label(r, text='—', font=FONT_S,
                             bg=C['bg2'], fg=C['fg'], anchor='w')
                v.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._info_lbl[key] = v

        # Suitability breakdown (one label per check)
        suit_frame = tk.Frame(info_outer, bg=C['bg2'])
        suit_frame.pack(fill=tk.X, pady=(5, 0))
        tk.Frame(info_outer, bg='#333', height=1).pack(fill=tk.X, pady=(4, 0))
        self._suit_rows: dict[str, tk.Label] = {}
        for key, label in [('ws',   'Envergadura'),
                            ('sch',  'Schengen'),
                            ('term', 'Terminal'),
                            ('ded',  'Dedicado')]:
            r = tk.Frame(suit_frame, bg=C['bg2'])
            r.pack(fill=tk.X, pady=1)
            tk.Label(r, text=f"{label}:", font=FONT_S,
                     bg=C['bg2'], fg=C['fg_dim'],
                     width=12, anchor='w').pack(side=tk.LEFT)
            lbl = tk.Label(r, text='—', font=FONT_S,
                           bg=C['bg2'], fg=C['fg_dim'], anchor='w')
            lbl.pack(side=tk.LEFT)
            self._suit_rows[key] = lbl

        # Assign button
        self.assign_btn = tk.Button(
            right, text="Assign Stand  ↵",
            font=('Consolas', 10, 'bold'),
            bg='#1b5e20', fg='#fff', activebackground='#2e7d32',
            disabledforeground='#444', relief=tk.FLAT, cursor='hand2',
            padx=10, pady=7, state=tk.DISABLED, command=self._assign_stand)
        self.assign_btn.pack(fill=tk.X, padx=8, pady=(0, 6))

    # ── Log ───────────────────────────────────────────────────────────────────

    def _build_log(self):
        wrap = tk.Frame(self, bg=C['bg3'], height=120)
        wrap.pack(fill=tk.X)
        wrap.pack_propagate(False)
        tk.Label(wrap, text=" Log", font=FONT_S, bg=C['bg3'],
                 fg=C['fg_dim'], anchor='w').pack(fill=tk.X, padx=8, pady=(3, 0))
        self.log_box = tk.Text(wrap, bg=C['bg3'], fg=C['fg_dim'], font=FONT_S,
                               relief=tk.FLAT, state=tk.DISABLED, wrap=tk.WORD)
        self.log_box.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
        for tag, col in [('info', C['accent']), ('ok', C['green']),
                          ('warn', C['orange']), ('err', C['red'])]:
            self.log_box.tag_config(tag, foreground=col)

    # ── Footer buttons ────────────────────────────────────────────────────────

    def _build_footer(self):
        bar = tk.Frame(self, bg=C['hdr'], pady=7)
        bar.pack(fill=tk.X)
        self.conn_btn = _btn(bar, "CONNECT TO AURORA", self._connect_aurora)
        self.conn_btn.pack(side=tk.LEFT, padx=(10, 4))
        _btn(bar, "QUERY SELECTED  (F5)", self._query_aurora,
             bg='#0a3d0a').pack(side=tk.LEFT, padx=4)
        _btn(bar, "ASIGNACIONES  ▤", self._open_assignments_panel,
             bg='#1a2a3a').pack(side=tk.LEFT, padx=4)
        _btn(bar, "CLEAR ALL STANDS", self._clear_occupied,
             bg='#3d0a0a').pack(side=tk.LEFT, padx=4)

    def _slabel(self, parent, text):
        tk.Label(parent, text=f"  {text}", font=FONT_S,
                 bg=C['bg'], fg=C['fg_dim'], anchor='w').pack(
                     fill=tk.X, pady=(8, 2))

    # ══════════════════════════════════════════════════════════════════════════
    # STRIP CARD
    # ══════════════════════════════════════════════════════════════════════════

    def _strip_empty(self):
        for w in self.strip_frame.winfo_children():
            w.destroy()
        tk.Label(self.strip_frame, text="Sin asignación",
                 font=FONT_S, bg=C['strip_bg'], fg='#aaa',
                 pady=16, padx=10).pack()

    def _strip_update(self, callsign, airline, aircraft, origin,
                      stand, sch_str, terminal):
        for w in self.strip_frame.winfo_children():
            w.destroy()
        f = self.strip_frame

        r1 = tk.Frame(f, bg=C['strip_bg'])
        r1.pack(fill=tk.X)
        tk.Label(r1, text=callsign or '—', font=FONT_L,
                 bg=C['strip_bg'], fg='#000', padx=6, pady=3).pack(side=tk.LEFT)
        tk.Label(r1, text=aircraft or '', font=('Consolas', 11),
                 bg=C['strip_bg'], fg='#333').pack(side=tk.LEFT, padx=6)
        t_bg = '#0d47a1' if terminal == 'T1' else \
               '#880e4f' if terminal == 'T2' else '#4e342e'
        tk.Label(r1, text=f" {terminal} ", font=('Consolas', 9, 'bold'),
                 bg=t_bg, fg='#fff').pack(side=tk.RIGHT, padx=5, pady=3)

        tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)

        r2 = tk.Frame(f, bg=C['strip_bg'])
        r2.pack(fill=tk.X)
        tk.Label(r2, text=airline or '', font=FONT_S,
                 bg=C['strip_bg'], fg='#444', padx=6, pady=2).pack(side=tk.LEFT)
        if origin:
            tk.Label(r2, text=origin, font=('Consolas', 9, 'bold'),
                     bg=C['strip_bg'], fg='#000').pack(side=tk.LEFT, padx=4)
        if sch_str:
            s_bg = '#1b5e20' if 'NON' not in sch_str else '#b71c1c'
            tk.Label(r2, text=f"  {sch_str}  ", font=('Consolas', 8),
                     bg=s_bg, fg='#fff', pady=2).pack(side=tk.LEFT, padx=4)

        tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)

        r3 = tk.Frame(f, bg='#111')
        r3.pack(fill=tk.X)
        if stand:
            tk.Label(r3, text=f"  STAND  {stand}  ",
                     font=('Consolas', 16, 'bold'),
                     bg='#111', fg='#fff', pady=5).pack(side=tk.LEFT)
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
            ok = self.aurora.connect()
            self.after(0, self._on_aurora_ok if ok else self._on_aurora_fail)
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
        self._my_callsign = self.aurora.get_connected_callsign() or ''
        suffix = f"  ({self._my_callsign})" if self._my_callsign else ''
        self._log(f"Connected to Aurora  (localhost:1130){suffix}", 'ok')
        self._sync_occupied_aurora()
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
            self._log("Aurora not connected", 'warn'); return
        cs = self.aurora.get_selected_callsign()
        if not cs:
            self._log("No traffic selected in Aurora", 'warn'); return
        fp = self.aurora.get_flight_plan(cs)
        if not fp:
            self._log(f"No flight plan for {cs}", 'warn'); return
        airline  = callsign_to_airline(cs) or ''
        aircraft = fp.get('aircraft', '')
        origin   = fp.get('departure', '')
        self.v_callsign.set(cs); self.v_airline.set(airline)
        self.v_aircraft.set(aircraft); self.v_origin.set(origin)
        self._log(f"Aurora FP: {cs} → {airline} {aircraft} from {origin}", 'info')
        self._run_query(cs, airline or None, aircraft or None, origin or None)

    def _clear_query(self):
        for v in (self.v_callsign, self.v_airline, self.v_aircraft, self.v_origin):
            v.set('')
        self.current_cs = ''

    def _query_manual(self):
        cs      = self.v_callsign.get().strip().upper() or None
        airline = self.v_airline.get().strip().upper()  or None
        acft    = self.v_aircraft.get().strip().upper() or None
        origin  = self.v_origin.get().strip().upper()   or None
        if not airline and not acft:
            messagebox.showwarning("Faltan campos",
                "Escribe al menos Airline o Aircraft.", parent=self)
            return
        self._run_query(cs, airline, acft, origin)

    def _run_query(self, callsign, airline_code, aircraft_type, origin):
        self.current_cs     = callsign or ''
        self.selected_stand = ''
        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵")

        # ── Wingspan (None if no aircraft) ────────────────────────────────────
        ws = None
        if aircraft_type:
            aircraft_type = pf.resolve_aircraft_type(aircraft_type, self.wingspans)
            ws = self.wingspans.get(aircraft_type)
            if ws is None:
                ws = simpledialog.askfloat(
                    "Avión desconocido",
                    f"'{aircraft_type}' no está en la base de datos.\nEnvergadura en metros:",
                    parent=self, minvalue=5.0, maxvalue=110.0)
                if ws:
                    self.wingspans[aircraft_type] = ws
                    try:
                        with open(pf.WINGSPANS_JSON, 'w', encoding='utf-8') as fh:
                            json.dump(dict(sorted(self.wingspans.items())), fh, indent=2)
                    except Exception:
                        pass
                ws = ws or 36.0
        self.acft_ws = ws or 0.0

        # ── Schengen: only if origin provided + not overridden ────────────────
        sch_override = self.seg['Schengen'].get()
        if sch_override == 'yes':
            sch = True
        elif sch_override == 'no':
            sch = False
        elif origin:
            prefix = origin[:2].upper()
            if prefix in pf.SCHENGEN_PREFIXES:
                sch = True
            elif prefix in pf.NON_SCHENGEN_PREFIXES:
                sch = False
            else:
                sch = messagebox.askyesno(
                    "¿Schengen?",
                    f"Prefijo '{prefix}' ({origin}) desconocido.\n¿Es vuelo Schengen?",
                    parent=self)
        else:
            sch = None   # no filter
        self.sch_bool = sch if sch is not None else True
        sch_str = ("SCHENGEN" if sch else "NON-SCHENGEN") if sch is not None else ""

        # ── Terminal override ─────────────────────────────────────────────────
        term_override = self.seg['Terminal'].get()

        # ── Build candidate pool ──────────────────────────────────────────────
        pool, terminal, label, fallback = self._build_pool(
            airline_code, aircraft_type, ws, sch, origin, term_override)

        # ── Apply type filter (gates / remote) ────────────────────────────────
        type_f = self.seg['Tipo'].get()
        if type_f == 'gates':
            pool = {k: v for k, v in pool.items() if not v.get('remote', False)}
        elif type_f == 'remote':
            pool = {k: v for k, v in pool.items() if v.get('remote', False)}

        self.current_dm = pool
        self._populate_table(pool, self.sch_bool, ws or 0.0, fallback=fallback)

        n = len(pool)
        extra = []
        if ws:     extra.append(f"{ws}m")
        if sch_str: extra.append(sch_str)
        if type_f != 'all': extra.append(type_f)
        extra_s = f"  ({', '.join(extra)})" if extra else ""
        fb_s = "FALLBACK  " if fallback else ""
        self._log(f"{fb_s}{label}{extra_s}  →  {n} stands",
                  'warn' if fallback else 'info')

        self._strip_update(callsign or airline_code or '—',
                           airline_code or '', aircraft_type or '',
                           origin or '', '', sch_str, terminal or '—')

    def _build_pool(self, airline_code, aircraft_type, ws, sch, origin, term_override):
        """Return (pool_dict, terminal, label, is_fallback)."""
        occupied = self.occupied
        parkings = self.parkings

        def _is_special(pid):
            """Returns True for 9xx special-use stands (excluded from default results)."""
            try: return 900 <= int(pid) <= 999
            except (ValueError, TypeError): return False

        # ── Only aircraft, no airline ─────────────────────────────────────────
        if not airline_code:
            pool = {}
            for pid, d in parkings.items():
                if pid in occupied: continue
                if _is_special(pid): continue
                if d.get('schengen') in ('ga', 'maintenance'): continue
                if ws and (d.get('max_wingspan') or 999) < ws: continue
                if sch is not None and not pf.schengen_ok(d, sch): continue
                if term_override in ('T1', 'T2') and d.get('terminal') != term_override: continue
                pool[pid] = d
            return pool, term_override or 'ALL', f"Aircraft {aircraft_type}", False

        # ── Cargo ─────────────────────────────────────────────────────────────
        if pf.get_airline_terminal(self.airlines, airline_code) == 'CARGO' \
                and airline_code not in pf.DEDICATED:
            pool = {pid: d for pid, d in parkings.items()
                    if d.get('schengen') == 'cargo'
                    and pid not in occupied
                    and not _is_special(pid)
                    and (d.get('max_wingspan') or 999) >= (ws or 0)}
            return pool, 'CARGO', f"CARGO {airline_code}", False

        # ── Dedicated ─────────────────────────────────────────────────────────
        if airline_code in pf.DEDICATED:
            ded_term = pf.DEDICATED_TERMINAL.get(airline_code, 'T1')
            other    = 'T2' if ded_term == 'T1' else 'T1'
            dedicated = {
                pid: parkings[pid] for pid in pf.DEDICATED[airline_code]
                if pid in parkings and pid not in occupied
                and (parkings[pid].get('max_wingspan') or 0) >= (ws or 0)
                and (sch is None or pf.schengen_ok(parkings[pid], sch))
            }
            if dedicated:
                return dedicated, ded_term, \
                       f"Dedicado {airline_code}", False
            # fallback
            term = term_override if term_override in ('T1','T2') else ded_term
            pool = {p: d for p, d in pf.filter_parkings(parkings, term, airline_code,
                                       ws or 0, sch if sch is not None else True,
                                       occupied).items() if not _is_special(p)}
            if not pool:
                pool = {p: d for p, d in pf.filter_parkings(parkings, other, airline_code,
                                           ws or 0, sch if sch is not None else True,
                                           occupied).items() if not _is_special(p)}
                return pool, other, f"{airline_code} fallback→{other}", True
            return pool, term, f"{airline_code} fallback→{term}", True

        # ── Standard ──────────────────────────────────────────────────────────
        terminal = pf.get_airline_terminal(self.airlines, airline_code)
        if terminal is None:
            ans = simpledialog.askstring(
                "Aerolínea desconocida",
                f"'{airline_code}' no está en la base de datos.\nTerminal (T1 / T2 / CARGO):",
                parent=self)
            terminal = (ans or 'T1').strip().upper()
            self.airlines[airline_code] = terminal

        if terminal == 'CARGO':
            pool = {pid: d for pid, d in parkings.items()
                    if d.get('schengen') == 'cargo'
                    and pid not in occupied
                    and not _is_special(pid)
                    and (d.get('max_wingspan') or 999) >= (ws or 0)}
            return pool, 'CARGO', f"CARGO {airline_code}", False

        if term_override in ('T1', 'T2'):
            terminal = term_override

        other = 'T2' if terminal == 'T1' else 'T1'

        # No wingspan/schengen filter if those weren't provided
        eff_ws  = ws or 0
        eff_sch = sch if sch is not None else True

        pool = {p: d for p, d in pf.filter_parkings(parkings, terminal, airline_code,
                                   eff_ws, eff_sch, occupied).items() if not _is_special(p)}
        if pool:
            lbl = airline_code
            if not aircraft_type: lbl += f" (sin WS)"
            if sch is None:       lbl += f" (sin SCH)"
            return pool, terminal, lbl, False

        pool = {p: d for p, d in pf.filter_parkings(parkings, other, airline_code,
                                   eff_ws, eff_sch, occupied).items() if not _is_special(p)}
        return pool, other, f"{airline_code} fallback→{other}", True

    # ── Table ─────────────────────────────────────────────────────────────────

    def _populate_table(self, data_map, sch, acft_ws, fallback=False):
        for r in self.tree.get_children():
            self.tree.delete(r)
        self.all_sorted = []
        if not data_map:
            self._clear_info()
            return
        prefer = 'schengen_only' if sch else 'non_schengen_only'
        self.all_sorted = sorted(
            data_map, key=lambda p: pf._sort_key(p, data_map[p], prefer, sch))
        for pid in self.all_sorted:
            d      = data_map[pid]
            ws     = d.get('max_wingspan')
            remote = d.get('remote', False)
            excl   = d.get('excludes', [])
            stype  = d.get('schengen', 'mixed')
            fit    = acft_ws and ws == acft_ws
            tag    = 'perfect' if fit else ('fallbk' if fallback else
                      ('remote' if remote else 'gate'))
            self.tree.insert('', 'end', iid=pid,
                              values=(pid,
                                      (f"{ws}m★" if fit else f"{ws}m") if ws else "?",
                                      'Remote' if remote else 'Gate',
                                      pf.SCHENGEN_LABELS.get(stype, stype),
                                      d.get('max_acft', '?'),
                                      ', '.join(excl) if excl else '—'),
                              tags=(tag,))
        if self.all_sorted:
            self.tree.selection_set(self.all_sorted[0])
            self.tree.focus(self.all_sorted[0])
            self.tree.see(self.all_sorted[0])

    # ── Stand info ────────────────────────────────────────────────────────────

    def _on_stand_select(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        pid = sel[0]
        self.selected_stand = pid
        self.assign_btn.config(state=tk.NORMAL,
                               text=f"Assign Stand  {pid}  ↵")
        self._show_stand_info(pid)

    def _lookup_stand(self):
        pid = self.v_stand_search.get().strip().upper()
        if not pid:
            return
        if pid not in self.parkings:
            self._log(f"Stand '{pid}' no encontrado", 'warn')
            self._clear_info()
            return
        # Highlight in table if present
        if self.tree.exists(pid):
            self.tree.selection_set(pid)
            self.tree.see(pid)
        self._show_stand_info(pid)
        self._log(f"Info stand {pid}", 'info')

    def _show_stand_info(self, pid):
        d = self.parkings.get(pid)
        if not d:
            self._clear_info(); return

        ws      = d.get('max_wingspan')
        remote  = d.get('remote', False)
        stype   = d.get('schengen', 'mixed')
        term    = d.get('terminal', '?')
        excl    = d.get('excludes', [])
        max_ac  = d.get('max_acft', '?')
        occupied = pid in self.occupied

        self._info_lbl['Stand'].config(text=pid, fg=C['accent'])
        self._info_lbl['Terminal'].config(text=term, fg=C['fg'])
        self._info_lbl['Tipo'].config(
            text='Remote' if remote else 'Gate',
            fg=C['orange'] if remote else '#a5d6a7')
        self._info_lbl['Max WS'].config(
            text=f"{ws} m" if ws else "?", fg=C['fg'])
        self._info_lbl['Max Acft'].config(text=str(max_ac), fg=C['fg'])
        self._info_lbl['Zona'].config(
            text=pf.SCHENGEN_LABELS.get(stype, stype), fg=C['fg_dim'])
        self._info_lbl['Excluye'].config(
            text=', '.join(excl) if excl else '—',
            fg=C['orange'] if excl else C['fg_dim'])
        self._info_lbl['Estado'].config(
            text="OCUPADO" if occupied else "Libre",
            fg=C['red'] if occupied else C['green'])

        # ── Suitability checks ────────────────────────────────────────────────
        airline     = self.v_airline.get().strip().upper()
        acft_ws     = self.acft_ws
        sch         = self.sch_bool

        def _ok(text):  return (text, C['green'])
        def _warn(text): return (text, C['orange'])
        def _na():       return ('—', C['fg_dim'])

        # Wingspan
        if acft_ws and ws is not None:
            if acft_ws <= ws:
                fit = "★ perfecto" if acft_ws == ws else f"✓ cabe  ({acft_ws}m ≤ {ws}m)"
                ws_r = _ok(fit)
            else:
                ws_r = _warn(f"✗ no cabe  ({acft_ws}m > {ws}m)")
        elif acft_ws and ws is None:
            ws_r = _ok("✓ sin límite")
        else:
            ws_r = _na()

        # Schengen
        if airline or acft_ws:
            ok_sch = pf.schengen_ok(d, sch)
            sch_r  = _ok("✓ OK") if ok_sch else _warn(
                f"✗ zona {pf.SCHENGEN_LABELS.get(stype, stype)}")
        else:
            sch_r = _na()

        # Terminal
        if airline:
            al_term = pf.get_airline_terminal(self.airlines, airline)
            if al_term is None:
                term_r = _na()
            elif al_term == term or al_term == 'CARGO':
                term_r = _ok(f"✓ {term}")
            else:
                term_r = _warn(f"✗ {airline} usa {al_term}")
        else:
            term_r = _na()

        # Dedicated restriction
        if stype == 'eju_ezy_ezs':
            ded_r = _ok("✓ tuyo") if airline in ('EJU','EZY','EZS') \
                    else _warn("✗ solo EasyJet")
        elif stype == 'ibe_dedicated':
            ded_r = _ok("✓ tuyo") if airline == 'IBE' \
                    else _warn("✗ solo Iberia")
        else:
            ded_r = _ok("✓ sin restricción") if airline else _na()

        for key, (text, col) in [('ws',   ws_r),
                                   ('sch',  sch_r),
                                   ('term', term_r),
                                   ('ded',  ded_r)]:
            self._suit_rows[key].config(text=text, fg=col)

    def _clear_info(self):
        for v in self._info_lbl.values():
            v.config(text='—', fg=C['fg_dim'])
        for v in self._suit_rows.values():
            v.config(text='—', fg=C['fg_dim'])

    # ══════════════════════════════════════════════════════════════════════════
    # ASSIGN
    # ══════════════════════════════════════════════════════════════════════════

    def _assign_stand(self):
        if not self.selected_stand:
            return
        stand = self.selected_stand
        data  = self.parkings.get(stand, {})
        excls = [ex for ex in data.get('excludes', []) if ex not in self.occupied]

        cs = self.current_cs or self.v_callsign.get().strip().upper() or '—'

        # ── Re-assignment: free old stand if this callsign already has one ─────
        if cs and cs != '—':
            for rec in self.assignments:
                if rec['cs'] == cs and rec['status'] in ('ASIGNADO', 'ASIGNADO(auto)', 'PRE-ASIGNADO'):
                    old_stand = rec['stand']
                    if old_stand != stand:
                        old_data = self.parkings.get(old_stand, {})
                        self.occupied.discard(old_stand)
                        self.occupied_by.pop(old_stand, None)
                        for ex in old_data.get('excludes', []):
                            self.occupied.discard(ex)
                        self._log(f"[RE]  {cs}: stand anterior {old_stand} liberado", 'warn')
                        # Mark old record as superseded
                        rec['status'] = 'REEMPLAZADO'
                        # Remove from pre-assigned if it was pending
                        self.preassigned.pop(cs, None)
                    break

        self.occupied.add(stand)
        for ex in data.get('excludes', []):
            self.occupied.add(ex)

        airline = self.v_airline.get().strip().upper()
        acft    = self.v_aircraft.get().strip().upper()
        origin  = self.v_origin.get().strip().upper()
        # Track who occupies this stand
        self.occupied_by[stand] = {'cs': cs, 'acft': acft, 'airline': airline}
        sch_str = ("SCHENGEN" if self.sch_bool else "NON-SCHENGEN")
        term    = pf.get_airline_terminal(self.airlines, airline) or \
                  data.get('terminal', 'T1')
        self._strip_update(cs, airline, acft, origin, stand, sch_str, term)

        for item in list(self.tree.get_children()):
            if item in ({stand} | set(data.get('excludes', []))):
                self.tree.delete(item)

        self.assign_btn.config(state=tk.DISABLED, text="Assign Stand  ↵")
        self.selected_stand = ''
        self._update_occupied()
        self._clear_info()

        blocked = f"  (blocked: {', '.join(excls)})" if excls else ""

        # Check if traffic is assumed before pushing to Aurora
        is_assumed = True
        if self.aurora.connected and cs and cs != '—':
            pos = self.aurora.get_traffic_position(cs)
            if pos is not None:
                is_assumed = bool(pos.get('assumed_station', '').strip())

        if self.aurora.connected and cs and cs != '—' and is_assumed:
            ok, detail = self.aurora.assign_gate(cs, stand)
            if ok:
                self._log(f"[OK]  {cs} → Stand {stand}{blocked}", 'ok')
                self._log(f"Aurora: {cs} gate {stand} set", 'ok')
            else:
                self._log(f"[OK]  {cs} → Stand {stand}{blocked}", 'ok')
                self._log(f"Aurora gate label: {detail}", 'warn')
            self._record_assignment(cs, airline, acft, origin, stand, 'ASIGNADO')
        elif self.aurora.connected and cs and cs != '—' and not is_assumed:
            # Pre-assign: reserve stand but wait for assumption
            self.preassigned[cs] = {
                'stand': stand, 'airline': airline, 'aircraft': acft,
                'origin': origin, 'time': datetime.datetime.now().strftime('%H:%M:%S')
            }
            self._log(f"[PRE]  {cs} → Stand {stand}{blocked}  (pendiente asunción)", 'warn')
            self._record_assignment(cs, airline, acft, origin, stand, 'PRE-ASIGNADO')
        else:
            self._log(f"[OK]  {cs} → Stand {stand}{blocked}", 'ok')
            self._record_assignment(cs, airline, acft, origin, stand, 'ASIGNADO')

        self._refresh_assignments_panel()
        self._refresh_occupied_panel()

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _update_occupied(self):
        if self.occupied:
            occ = sorted(self.occupied, key=lambda x: (pf.get_numeric_id(x), x))
            self.occ_label.config(text='  '.join(occ))
        else:
            self.occ_label.config(text='—')

    def _sync_occupied_aurora(self):
        """Fetch occupied gates from Aurora and merge into local occupied set."""
        if not self.aurora.connected:
            self._log("Aurora no conectado", 'warn')
            return
        self._log("Consultando gates ocupados en Aurora…", 'info')
        def _do():
            gates = self.aurora.get_occupied_gates()
            self.after(0, lambda: self._apply_aurora_gates(gates))
        threading.Thread(target=_do, daemon=True).start()

    def _apply_aurora_gates(self, gates: dict):
        if not gates:
            self._log("Aurora: ningún tráfico en tierra con gate asignado", 'warn')
            return
        added = []
        for gate, cs in gates.items():
            g = gate.strip().upper()
            if g and g not in self.occupied:
                self.occupied.add(g)
                self.occupied_by[g] = {'cs': cs, 'acft': '', 'airline': callsign_to_airline(cs) or ''}
                added.append(f"{g}({cs})")
        self._update_occupied()
        self._refresh_occupied_panel()
        # Refresh table to remove newly occupied stands
        for item in list(self.tree.get_children()):
            if item in self.occupied:
                self.tree.delete(item)
        if added:
            self._log(f"Sync Aurora: {len(added)} gates ocupados → {', '.join(added)}", 'ok')
        else:
            self._log(f"Sync Aurora: {len(gates)} tráficos, todos ya conocidos", 'info')

    def _clear_occupied(self):
        self.occupied.clear()
        self.occupied_by.clear()
        self._update_occupied()
        self._refresh_occupied_panel()
        self._log("All stands cleared", 'info')

    def _release_dialog(self):
        s = simpledialog.askstring("Liberar stand", "Stand ID:", parent=self)
        if not s: return
        s = s.strip().upper()
        if s in self.occupied:
            self.occupied.discard(s)
            self.occupied_by.pop(s, None)
            self._update_occupied()
            self._log(f"Released: {s}", 'info')
            if self._occ_win and self._occ_win.winfo_exists():
                self._refresh_occupied_panel()
        else:
            self._log(f"{s} no estaba ocupado", 'warn')

    def _open_occupied_panel(self):
        if self._occ_win and self._occ_win.winfo_exists():
            self._refresh_occupied_panel()
            self._occ_win.lift()
            return

        win = tk.Toplevel(self)
        win.title("Stands Ocupados")
        win.configure(bg=C['bg'])
        win.geometry('560x340')
        self._occ_win = win

        # Treeview
        cols = ('stand', 'callsign', 'aircraft', 'airline')
        style = ttk.Style(win)
        style.configure('Occ.Treeview',
                         background=C['bg2'], fieldbackground=C['bg2'],
                         foreground=C['fg'], rowheight=22, font=FONT_S,
                         borderwidth=0)
        style.configure('Occ.Treeview.Heading',
                         background=C['hdr'], foreground=C['accent'],
                         font=('Consolas', 9, 'bold'), relief='flat')
        style.map('Occ.Treeview', background=[('selected', C['seg_on'])])

        tree = ttk.Treeview(win, columns=cols, show='headings',
                             style='Occ.Treeview', selectmode='browse')
        tree.heading('stand',    text='Stand')
        tree.heading('callsign', text='Callsign')
        tree.heading('aircraft', text='Avión')
        tree.heading('airline',  text='Aerolínea')
        tree.column('stand',    width=80,  anchor='center')
        tree.column('callsign', width=120, anchor='center')
        tree.column('aircraft', width=100, anchor='center')
        tree.column('airline',  width=100, anchor='center')

        sb = ttk.Scrollbar(win, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=8)
        self._occ_tree = tree

        # Tag for stands with no callsign info (synced from Aurora raw)
        tree.tag_configure('known',   foreground=C['orange'])
        tree.tag_configure('unknown', foreground=C['fg_dim'])

        bar = tk.Frame(win, bg=C['bg'])
        bar.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=8)
        _btn(bar, "⟳ Refresh", self._refresh_occupied_panel,
             bg='#0a2a1a').pack(fill=tk.X, pady=(0, 4))
        _btn(bar, "x Liberar…", self._release_dialog,
             bg='#1a1a1a').pack(fill=tk.X, pady=(0, 4))
        _btn(bar, "Cerrar", win.destroy,
             bg=C['btn']).pack(fill=tk.X)

        self._refresh_occupied_panel()

    def _refresh_occupied_panel(self):
        if not self._occ_win or not self._occ_win.winfo_exists():
            return
        for row in self._occ_tree.get_children():
            self._occ_tree.delete(row)
        stands = sorted(self.occupied, key=lambda x: (pf.get_numeric_id(x), x))
        for s in stands:
            info = self.occupied_by.get(s, {})
            cs      = info.get('cs', '—')
            acft    = info.get('acft', '—')
            airline = info.get('airline', '—')
            tag = 'known' if cs and cs != '—' else 'unknown'
            self._occ_tree.insert('', 'end',
                                   values=(s, cs, acft, airline),
                                   tags=(tag,))

    def _log(self, msg, level='info'):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"{ts}  {msg}\n", level)
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)

    # ══════════════════════════════════════════════════════════════════════════
    # AUTO-REFRESH
    # ══════════════════════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════════════════════
    # ASSIGNMENTS PANEL
    # ══════════════════════════════════════════════════════════════════════════

    def _record_assignment(self, cs, airline, aircraft, origin, stand, status):
        self.assignments.append({
            'cs': cs, 'airline': airline, 'aircraft': aircraft,
            'origin': origin, 'stand': stand, 'status': status,
            'time': datetime.datetime.now().strftime('%H:%M:%S'),
        })

    def _open_assignments_panel(self):
        if self._assign_win and self._assign_win.winfo_exists():
            self._assign_win.lift()
            return

        win = tk.Toplevel(self)
        win.title("Stands Asignados / Pre-asignados")
        win.configure(bg=C['bg'])
        win.geometry('780x380')
        win.resizable(True, True)
        self._assign_win = win

        # Table
        style = ttk.Style(win)
        style.configure('A.Treeview',
                         background=C['bg2'], fieldbackground=C['bg2'],
                         foreground=C['fg'], rowheight=24, font=FONT_S)
        style.configure('A.Treeview.Heading',
                         background=C['hdr'], foreground=C['accent'],
                         font=('Consolas', 9, 'bold'), relief='flat')
        style.map('A.Treeview', background=[('selected', '#1565c0')])

        cols = ('Hora', 'Callsign', 'Aerolínea', 'Avión', 'Origen', 'Stand', 'Estado')
        self._atree = ttk.Treeview(win, columns=cols, show='headings',
                                    style='A.Treeview', selectmode='browse')
        cw = {'Hora':58, 'Callsign':80, 'Aerolínea':70, 'Avión':62,
              'Origen':62, 'Stand':58, 'Estado':100}
        for c in cols:
            self._atree.heading(c, text=c, anchor='w')
            self._atree.column(c, width=cw[c], anchor='w')

        self._atree.tag_configure('pre',  foreground=C['orange'])
        self._atree.tag_configure('done', foreground=C['green'])

        vsb = ttk.Scrollbar(win, orient='vertical', command=self._atree.yview)
        self._atree.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=8)
        self._atree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)

        # Buttons
        bf = tk.Frame(win, bg=C['hdr'], pady=6)
        bf.pack(fill=tk.X)
        _btn(bf, "Exportar CSV", self._export_assignments,
             bg='#1a2a1a').pack(side=tk.LEFT, padx=(8, 4))
        _btn(bf, "Limpiar historial", self._clear_assignments,
             bg='#2a1a1a').pack(side=tk.LEFT, padx=4)

        self._refresh_assignments_panel()

    def _refresh_assignments_panel(self):
        if not self._assign_win or not self._assign_win.winfo_exists():
            return
        for row in self._atree.get_children():
            self._atree.delete(row)
        for a in reversed(self.assignments):
            tag = 'pre' if a['status'] == 'PRE-ASIGNADO' else 'done'
            self._atree.insert('', 'end',
                                values=(a['time'], a['cs'], a['airline'],
                                        a['aircraft'], a['origin'],
                                        a['stand'], a['status']),
                                tags=(tag,))

    def _export_assignments(self):
        import csv
        path = os.path.join(BASE, f"assignments_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=['time','cs','airline','aircraft','origin','stand','status'])
            w.writeheader()
            w.writerows(self.assignments)
        self._log(f"Exportado: {os.path.basename(path)}", 'ok')

    def _clear_assignments(self):
        self.assignments.clear()
        self._refresh_assignments_panel()
        self._log("Historial de asignaciones limpiado", 'info')

    # ── Pre-assignment poller ─────────────────────────────────────────────────

    def _poll_preassigned(self):
        """Check if any pre-assigned traffic has been assumed."""
        if not self.preassigned or not self.aurora.connected:
            return
        for cs, info in list(self.preassigned.items()):
            pos = self.aurora.get_traffic_position(cs)
            if pos and pos.get('assumed_station', '').strip():
                stand = info['stand']
                ok, detail = self.aurora.assign_gate(cs, stand)
                if ok:
                    self.after(0, lambda c=cs, s=stand: (
                        self._log(f"[AUTO]  {c} asumido → gate {s} enviado a Aurora", 'ok'),
                        self._promote_preassigned(c)
                    ))
                else:
                    self.after(0, lambda c=cs, d=detail: (
                        self._log(f"[AUTO]  {c} asumido pero gate falló: {d}", 'warn'),
                    ))

    def _promote_preassigned(self, cs):
        """Move a callsign from pre-assigned to assigned."""
        if cs in self.preassigned:
            info = self.preassigned.pop(cs)
            # Update the assignment record status
            for a in self.assignments:
                if a['cs'] == cs and a['status'] == 'PRE-ASIGNADO':
                    a['status'] = 'ASIGNADO (auto)'
            self._refresh_assignments_panel()

    def _on_auto_toggle(self):
        if self._auto_var.get():
            if not self.aurora.connected:
                self._log("Auto-refresh requiere Aurora conectado", 'warn')
                self._auto_var.set(False); return
            self.auto_cb.config(fg=C['green'])
            self._log(f"Auto-refresh ON  ({self.POLL_MS//1000}s)", 'info')
            self._poll()
        else:
            self.auto_cb.config(fg=C['fg_dim'])
            self._stop_poll()
            self._log("Auto-refresh OFF", 'info')

    def _poll(self):
        if not self._auto_var.get() or not self.aurora.connected:
            return
        def _do():
            cs = self.aurora.get_selected_callsign()
            self.after(0, lambda: self._handle_poll(cs))
            # Also check pre-assigned traffic (runs in same thread)
            self._poll_preassigned()
        threading.Thread(target=_do, daemon=True).start()
        self._poll_job = self.after(self.POLL_MS, self._poll)

    def _handle_poll(self, cs):
        if not cs or cs == self._last_polled:
            return
        self._last_polled = cs
        fp = self.aurora.get_flight_plan(cs)
        if not fp: return
        airline  = callsign_to_airline(cs) or ''
        aircraft = fp.get('aircraft', '')
        origin   = fp.get('departure', '')
        if not airline and not aircraft: return
        self.v_callsign.set(cs); self.v_airline.set(airline)
        self.v_aircraft.set(aircraft); self.v_origin.set(origin)
        self._log(f"Auto: {cs} → {airline} {aircraft} from {origin}", 'info')
        self._run_query(cs, airline or None, aircraft or None, origin or None)

    def _stop_poll(self):
        if self._poll_job:
            self.after_cancel(self._poll_job)
            self._poll_job = None

    def _on_close(self):
        self._stop_poll()
        self.aurora.disconnect()
        self.destroy()


if __name__ == '__main__':
    try:
        app = ParkingApp()
        app.mainloop()
    except Exception as exc:
        import traceback, datetime
        _log_fh.write(f"\n[{datetime.datetime.now()}] CRASH:\n")
        traceback.print_exc(file=_log_fh)
        _log_fh.flush()
        try:
            import tkinter.messagebox as _mb
            _mb.showerror("LEBL Parking — Error",
                          f"La aplicación ha fallado:\n\n{exc}\n\nVer error.log para detalles.")
        except Exception:
            pass
