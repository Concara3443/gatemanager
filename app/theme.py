"""theme.py — Colors, fonts, and shared UI helpers."""
import tkinter as tk

# Palette
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
