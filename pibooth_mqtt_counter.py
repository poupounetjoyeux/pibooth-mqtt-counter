"""Plugin to send counters when its changing to an MQTT broker"""
import pibooth
import threading
import json
from pibooth.utils import LOGGER
from pibooth.counters import Counters

__version__ = "1.0.5"

mqtt_counters_attributes = ['mqtt_client', 'mqtt_topic', 'can_publish_mqtt', 'print_started', 'miss_paper', 'lock', 'pending_msgs']

class MqttCounters(Counters):

    def __init__(self, cfg, base_counter):
        super(MqttCounters, self).__init__(base_counter.filename, **base_counter.default.copy())
        if 'kwargs' in self.data:
            del self.data['kwargs']
        
        self.mqtt_topic = cfg.get('MQTT', 'topic')
        if not self.mqtt_topic:
            self.mqtt_topic = 'PiBooth'
            
        self.pending_msgs = []
        self.lock = threading.Lock()
        self.miss_paper = False
        self.print_started = False

        import paho.mqtt.client as mqtt
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, cfg.get('MQTT', 'client_id'))
        self.mqtt_client.on_connect = MqttCounters.on_connect
        self.mqtt_client.on_message = MqttCounters.on_message
        self.mqtt_client.on_publish = MqttCounters.on_publish
        self.mqtt_client.user_data_set(self)
        
        credentials = cfg.gettuple('MQTT', 'credentials', str)
        if credentials and len(credentials) == 2 and credentials[0] and credentials[1]:
            self.mqtt_client.username_pw_set(credentials[0], credentials[1])
            
        try:
            host = cfg.get('MQTT', 'broker_host')
            self.mqtt_client.connect(host, int(cfg.getfloat('MQTT', 'broker_port')), 60)
            self.mqtt_client.loop_start()
            LOGGER.info(f'Will push counters over MQTT broker {host}')
            self.can_publish_mqtt = True
        except Exception as e:
            LOGGER.error(f"Unable to connect to the MQTT broker {host} due to : {str(e)}")
            self.can_publish_mqtt = False
            
    def on_message(client, userdata, message):
        if not isinstance(userdata, MqttCounters):
            LOGGER.error(f"User data is not an MqttCounters..")
            return
            
        reset_topic = MqttCounters.get_reset_topic(userdata)
        if message.topic != reset_topic:
            LOGGER.error(f"We received a not expected message on topic {message.topic}")
            return
        
        if str(message.payload.decode("utf-8")).lower() != 'true':
            LOGGER.warn(f'Message received on topic {reset_topic} is not : true')
            return
            
        LOGGER.info("Recceived a valid reset counters signal from MQTT broker")
        userdata.reset()
        
    def get_reset_topic(counter):
        return f'{counter.mqtt_topic}/reset'
            
    def on_connect(client, userdata, flags, reason_code, properties):
        if not isinstance(userdata, MqttCounters):
            LOGGER.error(f"User data is not an MqttCounters..")
            return
            
        if reason_code.is_failure:
            LOGGER.error(f"Failed to connect: {reason_code}. will retry connection..")
        else:
            topic = MqttCounters.get_reset_topic(userdata)
            client.subscribe(topic)
            LOGGER.info(f"Subscribed to topic {topic}")
            
    def on_publish(client, userdata, mid, reason_code, properties):
        if not isinstance(userdata, MqttCounters):
            LOGGER.error(f"User data is not an MqttCounters..")
            return
            
        with userdata.lock:
            userdata.pending_msgs = list(filter(lambda msg: msg.mid != mid, userdata.pending_msgs))

    def __getattr__(self, name):
        if name in mqtt_counters_attributes:
            return super(Counters, self).__getattr__(name)
        return super(MqttCounters, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name in mqtt_counters_attributes:
            super(Counters, self).__setattr__(name, value)
            return
        if name == 'printed' and value == self.printed + 1:
            self.print_started = True
        super(MqttCounters, self).__setattr__(name, value)

    def reset(self):
        super(MqttCounters, self).reset()
        self.miss_paper = False
        self.publish_mqtt_counters('Reset')

    def publish_mqtt_counters(self, event):
        if not self.can_publish_mqtt:
            return
        try:
            payload = self.data.copy()
            payload['event'] = event
            with self.lock:
                msg_info = self.mqtt_client.publish(f'{self.mqtt_topic}/counters', json.dumps(payload))
                self.pending_msgs.append(msg_info)
            LOGGER.info('Counters published over MQTT')
        except Exception as e:
            LOGGER.error(f"Unable to publish counters over MQTT due to : {str(e)}")

    def disconnect(self):
        self.can_publish_mqtt = False
        self.mqtt_client.unsubscribe(MqttCounters.get_reset_topic(self))
        self.mqtt_client.on_publish = None
        with self.lock:
            LOGGER.info(f'There is {len(self.pending_msgs)} messages waiting to be published in the MQTT queue.. Waiting 3 seconds for publish to be finished..')
            for msg_info in self.pending_msgs:
                msg_info.wait_for_publish(3.0)
        
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()


def raise_printer_events(app):
    if not isinstance(app.count, MqttCounters) or not app.printer.is_installed():
        return
        
    if not app.printer.is_ready() and not app.count.miss_paper:
        app.count.miss_paper = True
        app.count.publish_mqtt_counters('MissPaper')

    if app.count.print_started:
        app.count.print_started = False
        app.count.publish_mqtt_counters('PrintStarted')

@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the new configuration options"""
    cfg.add_option('MQTT', 'broker_host', 'localhost', "The MQTT broker host")
    cfg.add_option('MQTT', 'broker_port', '1883', "The MQTT broker port")
    cfg.add_option('MQTT', 'credentials', ('', ''), "The MQTT username and password if needed. Must be formated like (username, password)")
    cfg.add_option('MQTT', 'client_id', 'PiBooth', "The MQTT client_id")
    cfg.add_option('MQTT', 'topic', 'PiBooth', "The MQTT topic to publish to")
    
@pibooth.hookimpl
def pibooth_startup(cfg, app):
    app.count = MqttCounters(cfg, app.count)
    app.printer.count = app.count

@pibooth.hookimpl
def state_wait_enter(cfg, app, win):
    if isinstance(app.count, MqttCounters):
        app.count.print_started = False

@pibooth.hookimpl
def state_processing_exit(cfg, app, win):
    if isinstance(app.count, MqttCounters):
        app.count.publish_mqtt_counters('NewPhoto')

@pibooth.hookimpl
def state_wait_do(cfg, app, win, events):
    raise_printer_events(app)

@pibooth.hookimpl
def state_print_exit(cfg, app, win): 
    raise_printer_events(app)

@pibooth.hookimpl
def pibooth_cleanup(app):
    if isinstance(app.count, MqttCounters):
        app.count.disconnect()
