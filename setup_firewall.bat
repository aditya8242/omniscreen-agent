@echo off
title OmniScreen Firewall Setup
echo Adding Windows Firewall inbound rules for OmniScreen (TCP 8765 + UDP 8766)...
netsh advfirewall firewall delete rule name="OmniScreen Reality Hub" >nul 2>&1
netsh advfirewall firewall delete rule name="OmniScreen UDP Discovery" >nul 2>&1
netsh advfirewall firewall add rule name="OmniScreen Reality Hub" dir=in action=allow protocol=TCP localport=8765 profile=any
netsh advfirewall firewall add rule name="OmniScreen UDP Discovery" dir=in action=allow protocol=UDP localport=8766 profile=any
echo.
echo Firewall configuration complete.
pause
