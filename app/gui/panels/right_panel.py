# right panel: table & details
import tkinter as tk
from tkinter import ttk

from app.theme import FONT, FONT_S, C, _btn


def build(app, parent):
    # build results table & info box
    right = tk.Frame(parent, bg=C["bg"])
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    _slabel(right, "Available stands")

    # treeview
    style = ttk.Style(right)
    style.theme_use("default")
    style.configure(
        "P.Treeview",
        background=C["bg2"],
        fieldbackground=C["bg2"],
        foreground=C["fg"],
        rowheight=24,
        font=FONT_S,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "P.Treeview.Heading",
        background=C["hdr"],
        foreground=C["accent"],
        font=("Consolas", 9, "bold"),
        relief="flat",
    )
    style.map("P.Treeview", background=[("selected", "#1565c0")], foreground=[("selected", "#fff")])

    # instant filter
    ff = tk.Frame(right, bg=C["bg"])
    ff.pack(fill=tk.X, padx=8, pady=(0, 3))
    tk.Label(ff, text="Filtrar:", font=FONT_S, bg=C["bg"], fg=C["fg_dim"]).pack(side=tk.LEFT)
    app.v_filter = tk.StringVar()
    fe = tk.Entry(
        ff,
        textvariable=app.v_filter,
        font=FONT,
        bg=C["entry_bg"],
        fg=C["fg"],
        insertbackground=C["fg"],
        relief=tk.FLAT,
        bd=4,
        width=14,
    )
    fe.pack(side=tk.LEFT, padx=(6, 4))
    app.v_filter_count = tk.StringVar(value="")
    tk.Label(ff, textvariable=app.v_filter_count, font=FONT_S, bg=C["bg"], fg=C["fg_dim"]).pack(
        side=tk.LEFT
    )

    tf = tk.Frame(right, bg=C["bg"])
    tf.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 4))
    cols = ("Stand", "Score", "Max WS", "Tipo", "Zona", "Max Acft", "Excluye")
    app.tree = ttk.Treeview(
        tf, columns=cols, show="headings", style="P.Treeview", selectmode="browse"
    )
    cw = {"Stand": 62, "Score": 52, "Max WS": 68, "Tipo": 62, "Zona": 88, "Max Acft": 72, "Excluye": 150}
    for c in cols:
        app.tree.heading(c, text=c, anchor="w")
        app.tree.column(c, width=cw[c], anchor="w", minwidth=30)
    vsb = ttk.Scrollbar(tf, orient="vertical", command=app.tree.yview)
    app.tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    app.tree.pack(fill=tk.BOTH, expand=True)

    app.tree.tag_configure("perfect", foreground=C["purple"])
    app.tree.tag_configure("gate", foreground="#a5d6a7")
    app.tree.tag_configure("remote", foreground=C["orange"])
    app.tree.tag_configure("fallbk", foreground="#ffee58")
    app.tree.bind("<<TreeviewSelect>>", app._on_stand_select)
    app.tree.bind("<Double-1>", lambda e: app._assign_stand())

    # quick search
    sh = tk.Frame(right, bg=C["bg"])
    sh.pack(fill=tk.X, padx=8, pady=(0, 2))
    tk.Label(sh, text="  Info stand", font=FONT_S, bg=C["bg"], fg=C["fg_dim"]).pack(side=tk.LEFT)
    app.v_stand_search = tk.StringVar()
    se = tk.Entry(
        sh,
        textvariable=app.v_stand_search,
        font=FONT,
        bg=C["entry_bg"],
        fg=C["fg"],
        insertbackground=C["fg"],
        relief=tk.FLAT,
        bd=4,
        width=8,
    )
    se.pack(side=tk.LEFT, padx=(8, 3))
    se.bind("<Return>", lambda e: app._lookup_stand())
    _btn(sh, "Search ▶", app._lookup_stand, bg="#1c2a4a").pack(side=tk.LEFT)

    # detail box
    io = tk.Frame(right, bg=C["bg2"], padx=10, pady=6)
    io.pack(fill=tk.X, padx=8, pady=(0, 4))
    app._info_lbl = {}
    flds = [
        ("Stand", "Stand"),
        ("Terminal", "Terminal"),
        ("Tipo", "Tipo"),
        ("Max WS", "Max WS"),
        ("Max Acft", "Max Acft"),
        ("Zona", "Zona"),
        ("Excluye", "Excluye"),
        ("Estado", "Estado"),
    ]
    grid = tk.Frame(io, bg=C["bg2"])
    grid.pack(fill=tk.X)
    ca, cb = tk.Frame(grid, bg=C["bg2"]), tk.Frame(grid, bg=C["bg2"])
    ca.pack(side=tk.LEFT, fill=tk.X, expand=True)
    cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
    pairs = [flds[i : i + 2] for i in range(0, len(flds), 2)]
    for (ka, la), (kb, lb) in pairs:
        for col, k, l in [(ca, ka, la), (cb, kb, lb)]:
            r = tk.Frame(col, bg=C["bg2"])
            r.pack(fill=tk.X, pady=1)
            tk.Label(
                r, text=f"{l}:", font=FONT_S, bg=C["bg2"], fg=C["fg_dim"], width=9, anchor="w"
            ).pack(side=tk.LEFT)
            v = tk.Label(r, text="—", font=FONT_S, bg=C["bg2"], fg=C["fg"], anchor="w")
            v.pack(side=tk.LEFT, fill=tk.X, expand=True)
            app._info_lbl[k] = v

    # score label
    score_row = tk.Frame(io, bg=C["bg2"])
    score_row.pack(fill=tk.X, pady=(4, 0))
    tk.Label(score_row, text="Score:", font=FONT_S, bg=C["bg2"], fg=C["fg_dim"], width=9, anchor="w").pack(
        side=tk.LEFT
    )
    app._score_lbl = tk.Label(score_row, text="—", font=FONT_S, bg=C["bg2"], fg=C["accent"], anchor="w")
    app._score_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # suitability checks
    sf = tk.Frame(io, bg=C["bg2"])
    sf.pack(fill=tk.X, pady=(5, 0))
    tk.Frame(io, bg="#333", height=1).pack(fill=tk.X, pady=(4, 0))
    app._suit_rows = {}
    for k, l in [
        ("ws", "Wingspan"),
        ("sch", "Schengen"),
        ("term", "Terminal"),
        ("ded", "Dedicated"),
    ]:
        r = tk.Frame(sf, bg=C["bg2"])
        r.pack(fill=tk.X, pady=1)
        tk.Label(
            r, text=f"{l}:", font=FONT_S, bg=C["bg2"], fg=C["fg_dim"], width=12, anchor="w"
        ).pack(side=tk.LEFT)
        lbl = tk.Label(r, text="—", font=FONT_S, bg=C["bg2"], fg=C["fg_dim"], anchor="w")
        lbl.pack(side=tk.LEFT)
        app._suit_rows[k] = lbl

    # auto-assign proposal banner (hidden by default)
    app._proposal_frame = tk.Frame(right, bg="#1a3a1a", padx=8, pady=5)
    app._proposal_lbl = tk.Label(
        app._proposal_frame, text="", font=FONT_S, bg="#1a3a1a", fg=C["green"], anchor="w"
    )
    app._proposal_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
    _btn(app._proposal_frame, "Asignar ↵", app._proposal_confirm, bg=C["seg_on"]).pack(
        side=tk.LEFT, padx=(4, 2)
    )
    _btn(app._proposal_frame, "Saltar", app._proposal_dismiss, bg="#3a1a1a").pack(side=tk.LEFT)

    # assign btn
    app.assign_btn = tk.Button(
        right,
        text="Assign Stand  ↵",
        font=("Consolas", 10, "bold"),
        bg="#1b5e20",
        fg="#fff",
        activebackground="#2e7d32",
        disabledforeground="#444",
        relief=tk.FLAT,
        cursor="hand2",
        padx=10,
        pady=7,
        state=tk.DISABLED,
        command=app._assign_stand,
    )
    app.assign_btn.pack(fill=tk.X, padx=8, pady=(0, 6))


def _slabel(p, t):
    tk.Label(p, text=f"  {t}", font=FONT_S, bg=C["bg"], fg=C["fg_dim"], anchor="w").pack(
        fill=tk.X, pady=(8, 2)
    )
