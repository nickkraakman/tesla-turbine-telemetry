# Tesla Turbine Telemetry

A sensor dashboard running on a Raspberry Pi to measure, display, and log key performance data for a Tesla Turbine.

![Tesla Turbine Telemetry dashboard screenshot](https://waveguide.blog/static/github/telemetry-dashboard-screenshot.png)


## Getting started

This is how you can get this project up an running on your Raspberry Pi.


### Requirements

The minimum hardware requirement is a Raspberry Pi Zero **2**, as a quad core CPU is needed to run this smoothly, as well as a monitor with an HDMI input.

Also, the following sensors are required:

- MEAS M32JM-00010B-100PG pressue & temperature sensor (2x)*
- QRD1114 optical sensor (1 or 2)

> *Make sure you get the "J" version, as only those have digital output. Check the [MEAS M3200 datasheet](https://eu.mouser.com/datasheet/2/418/8/ENG_DS_M3200_A19-1958281.pdf) for more details on the available variations of this sensor.

[Click here for the entire **bill of materials**](https://waveguide.blog/telemetry-bom)


### Installation

This project runs on Raspbian Lite with openbox, and has auto-login to console enabled, so the dashboard opens automatically on powering up the Pi.

Several additional packages were installed, and various customizations were made to the configs, so I highly recommend to use the link below to download the disk image instead of starting from scratch.

1. [Download latest disk image](https://waveguide.blog/telemetry-disk-image)
2. Insert SD card into computer (optionally format it as FAT32)
3. [Download Raspberry Pi Imager](https://www.raspberrypi.com/software/)
4. Open Raspberry Pi Imager >> Click "CHOOSE OS" >> Select "Use custom" at the bottom of the list >> Open the disk image from step #1 above
5. Click "CHOOSE STORAGE" and select your SD card, then click "WRITE"
6. Eject SD card from computer & insert it into your Raspberry Pi
7. Hook up the sensors to the Raspberry Pi according to the following schematic:
![Tesla Turbine Telemetry schematic](https://waveguide.blog/static/github/pinout-and-schematics.png)
1. Connect your Raspberry Pi to your monitor through HDMI & plug in the power cable, and you're good to go!

The Pi will take a minute or two to boot and auto-login, after which it will automatically launch the dashboard and will start reading data from the sensors.


### Optional installation steps

#### Hook up mouse
The dashboard allows you to change several settings, like whether you're measuring a single stage turbine or a multi-stage turbine for example, and this requires a mouse to be connected to your Pi.

On a Raspberry Pi Zero you'll need a micro USB **OTG** cable to connect the mouse.

#### Change settings
As mentioned above, you'll probably want to change the settings of your rotor dimensions for example to make sure the detailed figures shown in the dashboard are accurate for your setup.

#### Enable SSH
To gain more control over your Raspberry Pi, I strongly recommend you enable SSH, so you can use the command line to interact with your Pi.

To enable SSH:
1. Create an empty text file named `ssh` (without a file extension)
2. Insert your SD card into your computer
3. Copy the `ssh` file into the `Boot` folder
4. Eject SD card, insert it into your Pi, and power it up
5. Open `Terminal` on Mac, or [Putty](https://www.putty.org/) on Windows

You can now log in to your Pi by typing:
`ssh pi@turbine.local`, ENTER, and then as password `raspberry`, ENTER.

#### Connect to internet
If you're running this on a larger Rasbperry Pi, you can just plug in an ethernet cable, but if you're running it on a Raspberry Pi Zero 2 W, then you should follow these steps:

1. In a plain text editor create a new file called `wpa_supplicant.conf`
2. Copy/paste the following text into the file:
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
3. Replace `**YOUR ROUTER SSID**` with the name of your WiFi network, and replace `**YOUR ROUTER PASSWORD**` with your WiFi password
4. Insert your SD card into your computer
5. Copy `wpa_supplicant.conf` to the `Boot` folder
6. Eject SD card, insert it into your Pi, and power it up, your Pi will now be connected to the internet

#### Set up FTP access
Once your Pi is connected to the internet, you can now use an FTP tool like [FileZilla](https://filezilla-project.org/) to access the files on your Pi.

1. Download [FileZilla](https://filezilla-project.org/)
2. Click `File >> Site Manager >> New site`
3. Set the following settings:
![Tesla Turbine Telemetry dashboard screenshot](https://waveguide.blog/static/github/filezilla.png) Where the password is `raspberry`
4. Now click "Connect" to access the Pi's filesystem

#### Set up VNC
VNC allows you to use your computer as the screen, mouse, and keyboard for your Pi, which can be quite helpful.

1. [Download RealVNC Viewer](https://www.realvnc.com/en/connect/download/viewer/)
2. Click `File > New connection`
3. Fill in `turbine.local` as the VNC Server, then click "OK"
4. Now double-click the tile that appeared, and use the password `raspberry` when you're asked for it.

That's it!

**NOTE** VNC will show a black screen if you haven't connected a physical monitor to your Pi. I haven't found a way around this yet.

#### Hook up electronic valve
The dashboard has a "Play" icon at the top, which when pressed, turns on a pin on the Pi, which is intended to open and close an electronic valve.

I tested this with a [12V US Solid valve](https://www.amazon.nl/U-S-Solid-magneetventiel-aangestuurd-solenoid/dp/B01NBUFFEG?th=1) and the following circuit:

![Tesla Turbine Telemetry dashboard screenshot](https://waveguide.blog/static/github/valve-circuit.jpeg)

### Accessing the logs

Each time the RPM measurement goes from `0` to `>0`, the software will automatically start a new session, which is then logged to a CSV file for later analysis.

These files are stored in the `/telemetry/sessions` folder, and can be accessed through FTP.

The file names contain the time when the session started in the format `YYYYMMDDHHMMSS`


## Useful commands
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

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request