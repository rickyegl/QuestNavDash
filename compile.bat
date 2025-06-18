pyinstaller --onefile ^
--add-binary "wpiutil.dll;." ^
--add-binary "ntcore.dll;." ^
--add-binary "wpinet.dll;." ^
--hidden-import ntcore._logutil ^
 reef.py

start "" "saveBins.bat"