@echo off
REM Allow EasyPal-Next LAN gallery through Windows Firewall (run as Administrator)
echo Adding firewall rule for TCP port 8765...
netsh advfirewall firewall add rule name="EasyPal-Next LAN Gallery" dir=in action=allow protocol=TCP localport=8765 profile=private,domain
echo Done. Phone/tablet URL: http://192.168.1.3:8765  (use your PC's LAN IP if different)
pause
