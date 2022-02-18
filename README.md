Setup wifi
See: https://www.raspberrypi-spy.co.uk/2017/04/manually-setting-up-pi-wifi-using-wpa_supplicant-conf/
wpa_supplicant.conf
```
country=us
update_config=1
ctrl_interface=/var/run/wpa_supplicant

network={
 scan_ssid=1
 ssid="**YOUR ROUTER SSID**"
 psk="**YOUR ROUTER PASSWORD**"
}
```

SSH
ssh pi@turbine.local
raspberry

Check pigpio deamon status
`sudo service pigpiod status`

Check if MEAS sensor is connected properly:
`sudo i2cdetect -y 1` for the first, and `sudo i2cdetect -y 3` for the second sensor

Edit boot command
`sudo nano /etc/xdg/openbox/autostart`

Find all processes on port 8000
`lsof -i tcp:8000` or `netstat -vanp tcp | grep 8000`

Find and kill processes on port 8000
`kill -9 $(lsof -ti:8000)` or `lsof -t -i tcp:8000 | xargs kill`