@echo off
setlocal
cd /d "%~dp0web"
echo SCSBOA Score Studio - temporary local network test
echo.
echo This server is available to devices on your local network while this window stays open.
echo Press Ctrl+C to stop the server, then close this window.
echo.
echo Find this computer's IPv4 address with: ipconfig
echo On your phone, open: http://COMPUTER-IP:5174/?qa=1
echo Replace COMPUTER-IP with the IPv4 address of this computer.
echo Keep the phone and computer on the same trusted Wi-Fi network.
echo.
"C:\cloud coding\node.exe" "node_modules\vite\bin\vite.js" --host 0.0.0.0 --port 5174 --strictPort
echo.
echo The local network test server has stopped.
pause
