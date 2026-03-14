"""right_panel.py — Right panel builder for ParkingApp."""
import tkinter as tk
from tkinter import ttk
from app.theme import C, FONT, FONT_S, _btn
import app.parking_finder as pf


def build(app, parent):
    """Build the right panel and attach widgets to the app instance."""
    right = tk.Frame(parent, bg=C['bg'])
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    _slabel(right, "Stands disponibles")

    # Table
    style = ttk.Style(right)
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
    app.tree = ttk.Treeview(tf, columns=cols, show='headings',
                              style='P.Treeview', selectmode='browse')
    cw = {'Stand':62,'Max WS':68,'Tipo':62,'Zona':88,'Max Acft':72,'Excluye':180}
    for c in cols:
        app.tree.heading(c, text=c, anchor='w')
        app.tree.column(c, width=cw[c], anchor='w', minwidth=30)

    vsb = ttk.Scrollbar(tf, orient='vertical', command=app.tree.yview)
    app.tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    app.tree.pack(fill=tk.BOTH, expand=True)

    app.tree.tag_configure('perfect', foreground=C['purple'])
    app.tree.tag_configure('gate',    foreground='#a5d6a7')
    app.tree.tag_configure('remote',  foreground=C['orange'])
    app.tree.tag_configure('fallbk',  foreground='#ffee58')

    app.tree.bind('<<TreeviewSelect>>', app._on_stand_select)
    app.tree.bind('<Double-1>', lambda e: app._assign_stand())

    # Stand info box
    # Search bar
    sh = tk.Frame(right, bg=C['bg'])
    sh.pack(fill=tk.X, padx=8, pady=(0, 2))
    tk.Label(sh, text="  Info stand", font=FONT_S,
             bg=C['bg'], fg=C['fg_dim']).pack(side=tk.LEFT)
    app.v_stand_search = tk.StringVar()
    se = tk.Entry(sh, textvariable=app.v_stand_search, font=FONT,
                  bg=C['entry_bg'], fg=C['fg'], insertbackground=C['fg'],
                  relief=tk.FLAT, bd=4, width=8)
    se.pack(side=tk.LEFT, padx=(8, 3))
    se.bind('<Return>', lambda e: app._lookup_stand())
    _btn(sh, "Buscar ▶", app._lookup_stand,
         bg='#1c2a4a').pack(side=tk.LEFT)

    info_outer = tk.Frame(right, bg=C['bg2'], padx=10, pady=6)
    info_outer.pack(fill=tk.X, padx=8, pady=(0, 4))

    app._info_lbl = {}
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
            app._info_lbl[key] = v

    # Suitability breakdown (one label per check)
    suit_frame = tk.Frame(info_outer, bg=C['bg2'])
    suit_frame.pack(fill=tk.X, pady=(5, 0))
    tk.Frame(info_outer, bg='#333', height=1).pack(fill=tk.X, pady=(4, 0))
    app._suit_rows = {}
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
        app._suit_rows[key] = lbl

    # Assign button
    app.assign_btn = tk.Button(
        right, text="Assign Stand  ↵",
        font=('Consolas', 10, 'bold'),
        bg='#1b5e20', fg='#fff', activebackground='#2e7d32',
        disabledforeground='#444', relief=tk.FLAT, cursor='hand2',
        padx=10, pady=7, state=tk.DISABLED, command=app._assign_stand)
    app.assign_btn.pack(fill=tk.X, padx=8, pady=(0, 6))


def _slabel(parent, text):
    tk.Label(parent, text=f"  {text}", font=FONT_S,
             bg=C['bg'], fg=C['fg_dim'], anchor='w').pack(
                 fill=tk.X, pady=(8, 2))
