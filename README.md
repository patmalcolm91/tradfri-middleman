# Tradfri Middleman
This is a simple python script intended to be run as a daemon to work around a bug in Ikea Tradfri Bulbs. It is
intended to be used as a middleman between a home automation service (e.g. OpenHAB) and zigbee2mqtt (in MQTT
"attribute" mode).

## Problem Statement
Sending separate brightness and color temperature commands in short succession, such that the second message
is received by the bulb during the transition period of the first message results in the first transition
being cancelled before it is complete. The issue is described in detail
[in this zigbee2mqtt issue](https://github.com/Koenkk/zigbee2mqtt/issues/1810).

## How It Works
The daemon subscribes to topics ``tradfrimiddleman/+/set/brightness`` and ``tradfrimiddleman/+/set/color_temp`` (where ``+``
is a wildcard that corresponds to the zigbee identifier / friendly name) and forwards the message values on to the topic
``zigbee2mqtt/+/set`` in JSON format. If two values are received within a pre-defined time threshold of one another, the
the second forwarded message will contain both values.

### Example
If the following messages are received one shortly after another:
```
tradfrimiddleman/bulb1/set/brightness 255
tradfrimiddleman/bulb1/set/color_temp 400
```
This will result in the following two forwarded messages:
```
zigbee2mqtt/bulb1/set {"brightness": 255}
zigbee2mqtt/bulb1/set {"brightness": 255, "color_temp": 400}
```

### Unit Conversion
If the global variable ``CONVERT`` is set to ``True``, automatic unit conversions will be performed. This will be done
in both directions (i.e. both wheh when setting a value and when reporting a state).

|            | zigbee2mqtt unit | tradfrimiddleman unit |
|------------|------------------|-----------------------|
| brightness | raw (0-255)      | percent (0-100)       |
| color_temp | mired            | Kelvin                |

## Installation
Simply download the script file [tradfri-middleman.py](tradfri-middleman.py) from this repository, make sure you have
the python module "paho-mqtt" installed (``pip install paho-mqtt``), change the settings at the top of the file as
necessary, and run the script. It is recommended to install the script as a service on your home automation server
using, for example, systemd.

### Example systemd service setup (on Raspberry Pi)
Save the script to ``/home/pi/scripts/tradfri-middleman.py`` on your raspberry pi, and change the settings as necessary.

Create a file ``/etc/systemd/system/tradfri-middleman.service`` with the following contents:
```
[Unit]
Description=Tradfri MQTT Middleman Daemon
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/scripts/tradfri-middleman.py
User=pi
RestartSec=1
Restart=always

[Install]
WantedBy=multi-user.target
```

Run ``sudo systemctl start tradfri-middleman.service``, then ``sudo systemctl enable tradfri-middleman.service``.

The script is now configured to run as a background daemon and automatically launch at boot.