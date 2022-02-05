Setup wifi
wpa_supplicant.conf

SSH
ssh pi@turbine.local
raspberry

Edit boot command
`sudo nano /etc/xdg/openbox/autostart`

Find all processes on port 8000
`lsof -i tcp:8000` or `netstat -vanp tcp | grep 8000`

Find and kill processes on port 8000
`kill -9 $(lsof -ti:8000)` or `lsof -t -i tcp:8000 | xargs kill`