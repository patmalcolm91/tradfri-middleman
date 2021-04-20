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
# ================================================================================================

bulbs = {}


class Bulb:
    def __init__(self, bulb_identifier, client):
        self._client = client
        self.identifier = bulb_identifier
        self._topic = ZIGBEE2MQTT_PREFIX+"/"+self.identifier+"/set"
        self._t = None
        self._last_t_time = 0
        self._b = None
        self._last_b_time = 0

    @property
    def t(self):
        return self._t

    @t.setter
    def t(self, val):
        self._last_t_time = time.time()
        self._t = val.decode("utf-8")
        self._publish()

    @property
    def b(self):
        return self._b

    @b.setter
    def b(self, val):
        self._last_b_time = time.time()
        self._b = val.decode("utf-8")
        self._publish()

    def _purge_old(self):
        _current_time = time.time()
        if _current_time - self._last_t_time > COMBINE_THRESHOLD:
            self._t = None
        if _current_time - self._last_b_time > COMBINE_THRESHOLD:
            self._b = None

    def _publish(self):
        self._purge_old()
        _param_vals = [("\"brightness\"", self.b), ("\"color_temp\"", self.t)]
        payload = "{" + ", ".join([param+": "+val for param, val in _param_vals if val is not None]) + "}"
        print(self._topic, payload)
        self._client.publish(self._topic, payload, QOS, retain=RETAIN)


def on_message(client, userdata, msg):
    global bulbs
    _, bulb_identifier, _, param = msg.topic.split("/")
    if bulb_identifier not in bulbs:
        bulbs[bulb_identifier] = Bulb(bulb_identifier, client)
    if param == "brightness":
        bulbs[bulb_identifier].b = msg.payload
    elif param == "color_temp":
        bulbs[bulb_identifier].t = msg.payload


def on_client_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe(SUBSCRIBE_PREFIX+"/+/set/brightness")
    client.subscribe(SUBSCRIBE_PREFIX+"/+/set/color_temp")


if __name__ == "__main__":
    client = mqtt.Client()
    client.on_connect = on_client_connect
    client.on_message = on_message

    client.connect(BROKER_ADDRESS, BROKER_PORT, BROKER_KEEPALIVE)

    client.loop_forever()
