import sys
import os
def get_app_directory():
    if getattr(sys, 'frozen', False):  # Check if the app is frozen by PyInstaller
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return app_dir