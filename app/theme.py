# colors, fonts & helpers
import tkinter as tk

C = {
    'bg':       '#1a1a2e', 'bg2':  '#16213e', 'bg3':  '#0f0f23',
    'hdr':      '#0d0d1f', 'sep':  '#4fc3f7', 'accent':'#4fc3f7',
    'green':    '#66bb6a', 'orange':'#ffa726', 'red':  '#ef5350',
    'purple':   '#ce93d8', 'fg':   '#e0e0e0', 'fg_dim':'#757575',
    'strip_bg': '#fffde7', 'strip_sep':'#bdbdbd',
    'btn':      '#1c1c3a', 'btn_hl':'#2a2a50', 'entry_bg':'#0d1b35',
    'seg_on':   '#1565c0', 'seg_off':'#111122',
}
FONT, FONT_S, FONT_L, FONT_X = ('Consolas', 10), ('Consolas', 9), ('Consolas', 14, 'bold'), ('Consolas', 20, 'bold')

def _btn(p, t, c, bg=None, fg=None, **kw):
    return tk.Button(p, text=t, font=FONT_S, bg=bg or C['btn'], fg=fg or C['fg'], activebackground=C['btn_hl'], relief=tk.FLAT, cursor='hand2', padx=10, pady=5, command=c, **kw)

class SegGroup:
    # toggle button group
    def __init__(self, p, opts, d, on_change=None):
        self.var, self._btns, self._cb = tk.StringVar(value=d), {}, on_change
        for v, l in opts:
            b = tk.Button(p, text=l, font=FONT_S, relief=tk.FLAT, cursor='hand2', padx=8, pady=3, command=lambda v=v: self._pick(v)); b.pack(side=tk.LEFT, padx=1); self._btns[v] = b
        self._refresh()

    def _pick(self, v): self.var.set(v); self._refresh(); (self._cb(v) if self._cb else None)
    def _refresh(self):
        cur = self.var.get()
        for v, b in self._btns.items(): on = v == cur; b.config(bg=C['seg_on'] if on else C['seg_off'], fg=C['fg'] if on else C['fg_dim'])
    def get(self): return self.var.get()
