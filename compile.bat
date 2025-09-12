pyinstaller --onefile ^
--add-binary "wpiutil.dll;." ^
--add-binary "ntcore.dll;." ^
--add-binary "wpinet.dll;." ^
--hidden-import ntcore._logutil ^
 reef.py

 pyinstaller --onefile ^
--add-binary "wpiutil.dll;." ^
--add-binary "ntcore.dll;." ^
--add-binary "wpinet.dll;." ^
--hidden-import ntcore._logutil ^
 strategist_sim.py

  pyinstaller --onefile ^
--add-binary "wpiutil.dll;." ^
--add-binary "ntcore.dll;." ^
--add-binary "wpinet.dll;." ^
--hidden-import ntcore._logutil ^
 questnav.py

COPY /Y dist\reef.exe "%USERPROFILE%"
COPY /Y dist\strategist_sim.exe "%USERPROFILE%"

::start "" "saveBins.bat"