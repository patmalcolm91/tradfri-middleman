import paho.mqtt.client as mqtt
import time

# SETTINGS =======================================================================================
BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
BROKER_KEEPALIVE = 60
COMBINE_THRESHOLD = 1  # time threshold (seconds) for combining messages
SUBSCRIBE_PREFIX = "tradfrimiddleman"
ZIGBEE2MQTT_PREFIX = "zigbee2mqtt"
QOS = 0
RETAIN = False
CONVERT = False
REPORT_STATUS = True
SUPPRESS_COLOR_TEMP_WHEN_OFF = True  # don't send color_temp value when brightness is zero
MAX_BRIGHTNESS_VALUE = 254
# ================================================================================================

bulbs = {}


def mired_conversion(val):
    """Convert mired to Kelvin and vice versa."""
    return 1000000 / val


def brightness_to_percent(val):
    """Convert raw brightness (0-255) to a percent (0-100)."""
    return (val / MAX_BRIGHTNESS_VALUE) * 100


def percent_to_brightness(val):
    """Convert percent (0-100) to a raw brightness (0-255)."""
    return (val / 100) * MAX_BRIGHTNESS_VALUE


class Bulb:
    def __init__(self, bulb_identifier, client, convert=False):
        self._client = client
        self.identifier = bulb_identifier
        self._topic = ZIGBEE2MQTT_PREFIX+"/"+self.identifier+"/set"
        self._t = None
        self._last_t_time = 0
        self._b = None
        self._last_b_time = 0
        self._t_sent_while_off = False
        self.convert = convert

    @property
    def t(self):
        if self.convert:
            return None if self._t is None else mired_conversion(float(self._t))
        else:
            return self._t

    @t.setter
    def t(self, val):
        self._last_t_time = time.time()
        self._t = float(val.decode("utf-8"))
        if self._b is None or self._b == 0:
            self._t_sent_while_off = True
        self._publish()

    @property
    def b(self):
        if self.convert:
            return None if self._b is None else percent_to_brightness(float(self._b))
        else:
            return self._b

    @b.setter
    def b(self, val):
        self._last_b_time = time.time()
        self._b = float(val.decode("utf-8"))
        self._publish()
        if float(self._b) > 0:
            self._t_sent_while_off = False

    def _purge_old(self):
        _current_time = time.time()
        if _current_time - self._last_t_time > COMBINE_THRESHOLD:
            if self._t_sent_while_off:
                self._last_t_time = _current_time
            else:
                self._t = None
        if _current_time - self._last_b_time > COMBINE_THRESHOLD:
            self._b = None

    def _publish(self):
        self._purge_old()
        _param_vals = [("\"brightness\"", f"{self.b:0.2f}" if self.b is not None else "None")]
        if (self.b is None or self.b > 0) or not SUPPRESS_COLOR_TEMP_WHEN_OFF:
            _param_vals.append(("\"color_temp\"", f"{self.t:0.2f}" if self.t is not None else "None"))
        payload = "{" + ", ".join([param+": "+val for param, val in _param_vals if val != "None"]) + "}"
        print(self._topic, payload)
        self._client.publish(self._topic, payload, QOS, retain=RETAIN)


def on_message(client, userdata, msg):
    global bulbs
    if CONVERT and msg.topic.split("/")[0] == ZIGBEE2MQTT_PREFIX:
        _, bulb_identifier, param = msg.topic.split("/")
        if param == "brightness":
            b = float(msg.payload.decode("utf-8"))
            client.publish("/".join([SUBSCRIBE_PREFIX, bulb_identifier, param]), brightness_to_percent(b))
        elif param == "color_temp":
            ct = float(msg.payload.decode("utf-8"))
            client.publish("/".join([SUBSCRIBE_PREFIX, bulb_identifier, param]), mired_conversion(ct))
    else:
        _, bulb_identifier, _, param = msg.topic.split("/")
        if bulb_identifier not in bulbs:
            bulbs[bulb_identifier] = Bulb(bulb_identifier, client, convert=CONVERT)
        if param == "brightness":
            bulbs[bulb_identifier].b = msg.payload
        elif param == "color_temp":
            bulbs[bulb_identifier].t = msg.payload


def on_client_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    if REPORT_STATUS:
        client.publish("tradfrimiddleman/status", "online", qos=1, retain=True)
    client.subscribe(SUBSCRIBE_PREFIX+"/+/set/brightness")
    client.subscribe(SUBSCRIBE_PREFIX+"/+/set/color_temp")
    if CONVERT:
        client.subscribe(ZIGBEE2MQTT_PREFIX+"/+/brightness")
        client.subscribe(ZIGBEE2MQTT_PREFIX+"/+/color_temp")


if __name__ == "__main__":
    client = mqtt.Client()
    if REPORT_STATUS:
        client.will_set("tradfrimiddleman/status", "offline", retain=True)
    client.on_connect = on_client_connect
    client.on_message = on_message

    client.connect(BROKER_ADDRESS, BROKER_PORT, BROKER_KEEPALIVE)

    client.loop_forever()
