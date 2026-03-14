import sys, os, tkinter as tk
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def _resource(path):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, path)

from app.gui.app_window import ParkingApp

app = ParkingApp()
app.withdraw()  # hide main window while splash is shown

splash = tk.Toplevel(app)
splash.overrideredirect(True)
splash.attributes('-topmost', True)

_splash_ok = False
try:
    img = tk.PhotoImage(file=_resource('assets/splash.png'))
    w, h = img.width(), img.height()
    sw, sh = splash.winfo_screenwidth(), splash.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
    tk.Label(splash, image=img, bd=0).pack()
    splash.update()
    _splash_ok = True
except Exception:
    pass

if not _splash_ok:
    splash.destroy()
    app.deiconify()
else:
    app.after(2000, lambda: (splash.destroy(), app.deiconify()))

app.mainloop()
