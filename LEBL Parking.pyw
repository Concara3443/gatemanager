import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import pyi_splash
    pyi_splash.close()
except ImportError:
    pass

from app.gui.app_window import ParkingApp

app = ParkingApp()
app.mainloop()
