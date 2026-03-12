import runpy, os
runpy.run_path(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parking_gui.py'),
    run_name='__main__'
)
