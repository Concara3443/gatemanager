# occupied stands dialog
import tkinter as tk
from tkinter import ttk
from app.theme import C, FONT_S, _btn
import app.parking_finder as pf


def open(app):
    # open or raise window
    if app._occ_win and app._occ_win.winfo_exists(): refresh(app); app._occ_win.lift(); return
    win = tk.Toplevel(app); win.title("Stands Ocupados"); win.configure(bg=C['bg']); win.geometry('560x340'); app._occ_win = win

    # table
    cols = ('stand', 'callsign', 'aircraft', 'airline')
    style = ttk.Style(win)
    style.configure('Occ.Treeview', background=C['bg2'], fieldbackground=C['bg2'], foreground=C['fg'], rowheight=22, font=FONT_S, borderwidth=0)
    style.configure('Occ.Treeview.Heading', background=C['hdr'], foreground=C['accent'], font=('Consolas', 9, 'bold'), relief='flat')
    style.map('Occ.Treeview', background=[('selected', C['seg_on'])])

    tree = ttk.Treeview(win, columns=cols, show='headings', style='Occ.Treeview', selectmode='browse')
    tree.heading('stand', text='Stand'); tree.heading('callsign', text='Callsign'); tree.heading('aircraft', text='Avión'); tree.heading('airline', text='Aerolínea')
    tree.column('stand', width=80, anchor='center'); tree.column('callsign', width=120, anchor='center'); tree.column('aircraft', width=100, anchor='center'); tree.column('airline', width=100, anchor='center')

    sb = ttk.Scrollbar(win, orient='vertical', command=tree.yview); tree.configure(yscrollcommand=sb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=8); sb.pack(side=tk.LEFT, fill=tk.Y, pady=8); app._occ_tree = tree

    # tags
    tree.tag_configure('known', foreground=C['orange']); tree.tag_configure('unknown', foreground=C['fg_dim'])

    bar = tk.Frame(win, bg=C['bg']); bar.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=8)
    _btn(bar, "⟳ Refresh", lambda: refresh(app), bg='#0a2a1a').pack(fill=tk.X, pady=(0, 4))
    _btn(bar, "x Release…", app._release_dialog, bg='#1a1a1a').pack(fill=tk.X, pady=(0, 4))
    _btn(bar, "Close", win.destroy, bg=C['btn']).pack(fill=tk.X)
    refresh(app)


def refresh(app):
    # refresh list from app.occupied
    if not app._occ_win or not app._occ_win.winfo_exists(): return
    for r in app._occ_tree.get_children(): app._occ_tree.delete(r)
    stands = sorted(app.occupied, key=lambda x: (pf.get_numeric_id(x), x))
    for s in stands:
        i = app.occupied_by.get(s, {}); cs, ac, air = i.get('cs', '—'), i.get('acft', '—'), i.get('airline', '—')
        tag = 'known' if cs and cs != '—' else 'unknown'
        app._occ_tree.insert('', 'end', values=(s, cs, ac, air), tags=(tag,))
