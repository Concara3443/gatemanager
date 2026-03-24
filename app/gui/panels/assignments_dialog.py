# assignments history dialog
import csv
import datetime
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.theme import FONT_S, C, _btn


def open(app):
    # open or raise window
    if app._assign_win and app._assign_win.winfo_exists():
        app._assign_win.lift()
        return
    win = tk.Toplevel(app)
    win.title("Stands Asignados / Pre-asignados")
    win.configure(bg=C["bg"])
    win.geometry("780x380")
    win.resizable(True, True)
    app._assign_win = win

    # table
    style = ttk.Style(win)
    style.configure(
        "A.Treeview",
        background=C["bg2"],
        fieldbackground=C["bg2"],
        foreground=C["fg"],
        rowheight=24,
        font=FONT_S,
    )
    style.configure(
        "A.Treeview.Heading",
        background=C["hdr"],
        foreground=C["accent"],
        font=("Consolas", 9, "bold"),
        relief="flat",
    )
    style.map("A.Treeview", background=[("selected", "#1565c0")])

    cols = ("Hora", "Callsign", "Aerolínea", "Avión", "Origen", "Stand", "Estado")
    app._atree = ttk.Treeview(
        win, columns=cols, show="headings", style="A.Treeview", selectmode="browse"
    )
    cw = {
        "Hora": 58,
        "Callsign": 80,
        "Aerolínea": 70,
        "Avión": 62,
        "Origen": 62,
        "Stand": 58,
        "Estado": 100,
    }
    for c in cols:
        app._atree.heading(c, text=c, anchor="w")
        app._atree.column(c, width=cw[c], anchor="w")
    app._atree.tag_configure("pre", foreground=C["orange"])
    app._atree.tag_configure("done", foreground=C["green"])

    vsb = ttk.Scrollbar(win, orient="vertical", command=app._atree.yview)
    app._atree.configure(yscrollcommand=vsb.set)
    vsb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 4), pady=8)
    app._atree.pack(fill=tk.BOTH, expand=True, padx=(8, 0), pady=8)

    # footer btns
    bf = tk.Frame(win, bg=C["hdr"], pady=6)
    bf.pack(fill=tk.X)
    _btn(bf, "Export CSV", lambda: _export_csv(app), bg="#1a2a1a").pack(side=tk.LEFT, padx=(8, 4))
    _btn(bf, "Export JSON", lambda: _export_json(app), bg="#1a2a3a").pack(side=tk.LEFT, padx=4)
    _btn(bf, "Import JSON", lambda: _import_json(app), bg="#2a1a3a").pack(side=tk.LEFT, padx=4)
    _btn(bf, "Clear history", lambda: _clear_assignments(app), bg="#2a1a1a").pack(
        side=tk.LEFT, padx=4
    )
    refresh(app)


def refresh(app):
    # sync table from app.assignments
    if not app._assign_win or not app._assign_win.winfo_exists():
        return
    for r in app._atree.get_children():
        app._atree.delete(r)
    for a in reversed(app.assignments):
        tag = "pre" if a["status"] == "PRE-ASIGNADO" else "done"
        app._atree.insert(
            "",
            "end",
            values=(
                a["time"],
                a["cs"],
                a["airline"],
                a["aircraft"],
                a["origin"],
                a["stand"],
                a["status"],
            ),
            tags=(tag,),
        )


def _export_csv(app):
    # save to downloads
    dl = os.path.join(os.path.expanduser("~"), "Downloads")
    base = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    path = os.path.join(
        dl if os.path.isdir(dl) else base,
        f"assignments_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    )
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f, fieldnames=["time", "cs", "airline", "aircraft", "origin", "stand", "status"]
            )
            w.writeheader()
            w.writerows(app.assignments)
        app._log(f"Exported: {path}", "ok")
    except Exception as e:
        app._log(f"Export error: {e}", "error")
        messagebox.showerror("Export Error", f"Could not export:\n{e}")


def _export_json(app):
    dl = os.path.join(os.path.expanduser("~"), "Downloads")
    base = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    default_name = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path = filedialog.asksaveasfilename(
        initialdir=dl if os.path.isdir(dl) else base,
        initialfile=default_name,
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        title="Guardar sesión",
    )
    if not path:
        return
    session = {
        "airport": app.icao,
        "exported_at": datetime.datetime.now().isoformat(),
        "assignments": app.assignments,
        "occupied": list(app.occupied),
        "occupied_by": app.occupied_by,
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        app._log(f"Sesión exportada: {path}", "ok")
    except Exception as e:
        app._log(f"Export error: {e}", "error")
        messagebox.showerror("Error", f"No se pudo exportar:\n{e}")


def _import_json(app):
    dl = os.path.join(os.path.expanduser("~"), "Downloads")
    path = filedialog.askopenfilename(
        initialdir=dl if os.path.isdir(dl) else os.path.expanduser("~"),
        filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        title="Cargar sesión",
    )
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as f:
            session = json.load(f)
    except Exception as e:
        app._log(f"Import error: {e}", "error")
        messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
        return

    imported_airport = session.get("airport", "")
    if imported_airport and imported_airport != app.icao:
        if not messagebox.askyesno(
            "Aeropuerto distinto",
            f"La sesión es de {imported_airport} pero estás en {app.icao}.\n¿Importar igualmente?",
        ):
            return

    app.assignments = session.get("assignments", [])
    app.occupied = set(session.get("occupied", []))
    app.occupied_by = session.get("occupied_by", {})
    app._update_occupied()
    app._refresh_occupied_panel()
    refresh(app)
    # enable undo if there are active assignments
    active = ("ASIGNADO", "ASIGNADO(auto)", "PRE-ASIGNADO")
    if any(r["status"] in active for r in app.assignments):
        app.undo_btn.config(state=tk.NORMAL)
    exported_at = session.get("exported_at", "")
    app._log(f"Sesión importada: {imported_airport or '?'} ({exported_at[:16]})", "ok")


def _clear_assignments(app):
    app.assignments.clear()
    refresh(app)
    app._log("History cleared", "info")
