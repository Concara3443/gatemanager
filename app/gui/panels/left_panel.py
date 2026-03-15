# left panel: inputs & filters
import tkinter as tk
from app.theme import C, FONT, FONT_S, FONT_L, _btn, SegGroup


def build(app, parent):
    # build left side panel
    left = tk.Frame(parent, bg=C['bg'], width=320)
    left.pack(side=tk.LEFT, fill=tk.Y); left.pack_propagate(False)

    # query inputs
    _slabel(left, "Query  (1, 2 or 3 fields)")
    inp = tk.Frame(left, bg=C['bg2'], padx=8, pady=6)
    inp.pack(fill=tk.X, padx=8, pady=(0, 2))

    app.v_callsign, app.v_airline, app.v_aircraft, app.v_origin = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()

    # cs row + ga toggle
    cs_row = tk.Frame(inp, bg=C['bg2']); cs_row.pack(fill=tk.X, pady=2)
    tk.Label(cs_row, text=f"{'Callsign':<9}", font=FONT_S, bg=C['bg2'], fg=C['fg_dim'], width=9, anchor='w').pack(side=tk.LEFT)
    tk.Entry(cs_row, textvariable=app.v_callsign, font=FONT, bg=C['entry_bg'], fg=C['fg'], insertbackground=C['fg'], relief=tk.FLAT, bd=4, width=13).pack(side=tk.LEFT, fill=tk.X, expand=True)
    app.v_callsign.trace_add('write', lambda *_: app._on_callsign_change())

    app._ga_var = tk.BooleanVar(value=False)
    app._ga_btn = tk.Checkbutton(cs_row, text="GA", font=FONT_S, variable=app._ga_var, bg=C['bg2'], fg=C['fg_dim'], selectcolor=C['seg_on'], activebackground=C['bg2'], activeforeground=C['fg'], indicatoron=False, padx=6, pady=2, relief=tk.FLAT, cursor='hand2', command=app._on_ga_toggle)
    app._ga_btn.pack(side=tk.LEFT, padx=(4, 0))
    app._country_lbl = tk.Label(cs_row, text='', font=('Consolas', 8), bg=C['bg2'], fg=C['fg_dim']); app._country_lbl.pack(side=tk.LEFT, padx=(3, 0))

    fields = [("Airline", app.v_airline, "optional"), ("Aircraft", app.v_aircraft, "optional"), ("Origin", app.v_origin, "optional")]
    for lbl, var, hint in fields:
        row = tk.Frame(inp, bg=C['bg2']); row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=f"{lbl:<9}", font=FONT_S, bg=C['bg2'], fg=C['fg_dim'], width=9, anchor='w').pack(side=tk.LEFT)
        tk.Entry(row, textvariable=var, font=FONT, bg=C['entry_bg'], fg=C['fg'], insertbackground=C['fg'], relief=tk.FLAT, bd=4, width=13).pack(side=tk.LEFT, fill=tk.X, expand=True)
        if hint: tk.Label(row, text=hint, font=('Consolas', 8), bg=C['bg2'], fg=C['fg_dim']).pack(side=tk.LEFT, padx=3)

    # filters
    _slabel(left, "Filters")
    flt = tk.Frame(left, bg=C['bg2'], padx=8, pady=6); flt.pack(fill=tk.X, padx=8, pady=(0, 2))
    filter_rows = [("Tipo", [('all','All'), ('gates','Gates'), ('remote','Remote')]), ("Schengen", [('auto','Auto'), ('yes','SCH'), ('no','No-SCH')]), ("Terminal", [('auto','Auto'), ('T1','T1'), ('T2','T2')])]
    app.seg = {}
    for l, opts in filter_rows:
        row = tk.Frame(flt, bg=C['bg2']); row.pack(fill=tk.X, pady=2)
        tk.Label(row, text=f"{l:<9}", font=FONT_S, bg=C['bg2'], fg=C['fg_dim'], width=9, anchor='w').pack(side=tk.LEFT)
        sf = tk.Frame(row, bg=C['bg2']); sf.pack(side=tk.LEFT); app.seg[l] = SegGroup(sf, opts, opts[0][0])

    # buttons
    brow = tk.Frame(inp, bg=C['bg2']); brow.pack(fill=tk.X, pady=(6, 2))
    _btn(brow, "Query  ▶", app._query_manual, bg='#0d47a1').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
    _btn(brow, "Aurora  F5", app._query_aurora, bg='#1b5e20').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 3))
    _btn(brow, "✕", app._clear_query, bg='#2a1010', fg=C['red']).pack(side=tk.LEFT)

    # strip
    _slabel(left, "Current Strip")
    sf = tk.Frame(left, bg=C['bg'], padx=8); sf.pack(fill=tk.X)
    app.strip_frame = tk.Frame(sf, bg=C['strip_bg'], bd=1, relief=tk.SOLID); app.strip_frame.pack(fill=tk.X); _strip_empty(app)

    # occupied
    _slabel(left, "Occupied stands")
    of = tk.Frame(left, bg=C['bg'], padx=8); of.pack(fill=tk.X)
    app.occ_label = tk.Label(of, text="—", font=FONT_S, bg=C['bg2'], fg=C['orange'], anchor='nw', justify='left', wraplength=280, padx=6, pady=5); app.occ_label.pack(fill=tk.X)
    obs = tk.Frame(of, bg=C['bg']); obs.pack(fill=tk.X, pady=(3, 0))
    _btn(obs, "⟳  Sync Aurora", app._sync_occupied_aurora, bg='#0a2a1a').pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))
    _btn(obs, "▦  View all", app._open_occupied_panel, bg='#1a2a3a').pack(side=tk.LEFT, fill=tk.X, expand=True)
    _btn(of, "x  Release…", app._release_dialog, bg='#1a1a1a').pack(fill=tk.X, pady=(2, 0))


def _slabel(p, t): tk.Label(p, text=f"  {t}", font=FONT_S, bg=C['bg'], fg=C['fg_dim'], anchor='w').pack(fill=tk.X, pady=(8, 2))

def _strip_empty(app):
    for w in app.strip_frame.winfo_children(): w.destroy()
    tk.Label(app.strip_frame, text="No assignment", font=FONT_S, bg=C['strip_bg'], fg='#aaa', pady=16, padx=10).pack()

def _strip_update(app, cs, air, acft, dep, st, sch, term):
    # update strip ui
    for w in app.strip_frame.winfo_children(): w.destroy()
    f = app.strip_frame
    r1 = tk.Frame(f, bg=C['strip_bg']); r1.pack(fill=tk.X)
    tk.Label(r1, text=cs or '—', font=FONT_L, bg=C['strip_bg'], fg='#000', padx=6, pady=3).pack(side=tk.LEFT)
    tk.Label(r1, text=acft or '', font=('Consolas', 11), bg=C['strip_bg'], fg='#333').pack(side=tk.LEFT, padx=6)
    tbg = '#0d47a1' if term == 'T1' else '#880e4f' if term == 'T2' else '#4e342e'
    tk.Label(r1, text=f" {term} ", font=('Consolas', 9, 'bold'), bg=tbg, fg='#fff').pack(side=tk.RIGHT, padx=5, pady=3)
    tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)
    r2 = tk.Frame(f, bg=C['strip_bg']); r2.pack(fill=tk.X)
    tk.Label(r2, text=air or '', font=FONT_S, bg=C['strip_bg'], fg='#444', padx=6, pady=2).pack(side=tk.LEFT)
    if dep: tk.Label(r2, text=dep, font=('Consolas', 9, 'bold'), bg=C['strip_bg'], fg='#000').pack(side=tk.LEFT, padx=4)
    if sch:
        sbg = '#1b5e20' if 'NON' not in sch else '#b71c1c'
        tk.Label(r2, text=f"  {sch}  ", font=('Consolas', 8), bg=sbg, fg='#fff', pady=2).pack(side=tk.LEFT, padx=4)
    tk.Frame(f, bg=C['strip_sep'], height=1).pack(fill=tk.X)
    r3 = tk.Frame(f, bg='#111'); r3.pack(fill=tk.X)
    if st:
        tk.Label(r3, text=f"  STAND  {st}  ", font=('Consolas', 16, 'bold'), bg='#111', fg='#fff', pady=5).pack(side=tk.LEFT)
        tk.Label(r3, text="ASSIGNED", font=('Consolas', 8), bg='#111', fg=C['green']).pack(side=tk.LEFT, padx=4)
    else: tk.Label(r3, text="  STAND  —  PENDING", font=('Consolas', 12), bg='#111', fg='#555', pady=5).pack()
