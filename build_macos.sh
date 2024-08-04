#!/bin/sh

# Generate application package
pyinstaller --windowed --onefile main.py systemTheme.py utils.py -n photoHopper

# Create installer
create-dmg --volname "photoHopper" --window-pos 200 120 --window-size 600 300 --icon-size 100 --icon "photoHopper.app" 175 120 --app-drop-link 425 120 --hide-extension "photoHopper.app" "photoHopper.dmg" "dmg/"