import sys
import subprocess

def getSysTheme():
    if sys.platform == "darwin":
        return is_dark_mode_macos()
    elif sys.platform == "win32":
        return is_dark_mode_windows()
    else:
        return 3  # Unsupported platform

def is_dark_mode_macos():
    try:
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True
        )
        if "Dark" in result.stdout:
            return 1
        else:
            return 0
    except Exception as e:
        print(f"Could not determine macOS theme: {e}")
        return 0

def is_dark_mode_windows():
    import ctypes
    import winreg

    try:
        # Windows 10/11 system theme
        registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
        key = winreg.OpenKey(registry, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
        winreg.CloseKey(key)
        return 0 if value == 0 else 1
    except Exception as e:
        print(f"Could not determine Windows theme: {e}")
        return 0