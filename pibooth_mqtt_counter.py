"""Plugin to send counters when its changing to an MQTT broker"""
import pibooth
import json
from pibooth.utils import LOGGER
from pibooth.counters import Counters

__version__ = "1.0.3"

mqtt_counters_attributes = ['mqtt_client', 'mqtt_topic', 'can_publish_mqtt']

class MqttCounters(Counters):

    def __init__(self, cfg, base_counter):
        super(MqttCounters, self).__init__(base_counter.filename, **base_counter.default.copy())
        if 'kwargs' in self.data:
            del self.data['kwargs']
        
        import paho.mqtt.client as mqtt
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, cfg.get('MQTT', 'client_id'))
        self.mqtt_topic = cfg.get('MQTT', 'topic')
        
        credentials = cfg.gettuple('MQTT', 'credentials', str)
        if credentials and len(credentials) == 2 and credentials[0] and credentials[1]:
            self.mqtt_client.username_pw_set(credentials[0], credentials[1])
            
        try:
            host = cfg.get('MQTT', 'broker_host')
            self.mqtt_client.connect(host, int(cfg.getfloat('MQTT', 'broker_port')), 60)
            LOGGER.info(f'Will push counters over MQTT broker {host}')
            self.can_publish_mqtt = True
        except Exception as e:
            LOGGER.error(f"Unable to connect to the MQTT broker {host} due to : {str(e)}")
            self.can_publish_mqtt = False

    def __getattr__(self, name):
        if name in mqtt_counters_attributes:
            return super(Counters, self).__getattr__(name)
        return super(MqttCounters, self).__getattr__(name)

    def __setattr__(self, name, value):
        if name in mqtt_counters_attributes:
            super(Counters, self).__setattr__(name, value)
            return
        super(MqttCounters, self).__setattr__(name, value)

    def reset(self):
        super(MqttCounters, self).reset()
        self.publish_mqtt_counters('Reset')

    def publish_mqtt_counters(self, event):
        if not self.can_publish_mqtt:
            return
            
        try:
            payload = self.data.copy()
            payload['event'] = event
            self.mqtt_client.loop_start()
            msg_info = self.mqtt_client.publish(self.mqtt_topic, json.dumps(payload))
            msg_info.wait_for_publish()
            LOGGER.info('Counters published over MQTT')
        except Exception as e:
            LOGGER.error(f"Unable to publish counters over MQTT due to : {str(e)}")
        finally:
            self.mqtt_client.loop_stop()

    def disconnect(self):
        self.mqtt_client.disconnect()

@pibooth.hookimpl
def pibooth_configure(cfg):
    """Declare the new configuration options"""
    cfg.add_option('MQTT', 'broker_host', 'localhost', "The MQTT broker host")
    cfg.add_option('MQTT', 'broker_port', '1883', "The MQTT broker port")
    cfg.add_option('MQTT', 'credentials', ('', ''), "The MQTT username and password if needed. Must be formated like (username, password)")
    cfg.add_option('MQTT', 'client_id', 'PiBooth', "The MQTT client_id")
    cfg.add_option('MQTT', 'topic', 'PiBooth/counter', "The MQTT topic to publish to")
    
@pibooth.hookimpl
def pibooth_startup(cfg, app):
    app.count = MqttCounters(cfg, app.count)
    app.printer.count = app.count
    
@pibooth.hookimpl
def state_finish_exit(app):
    if isinstance(app.count, MqttCounters):
        app.count.publish_mqtt_counters('NewPhoto')

@pibooth.hookimpl
def state_wait_do(cfg, app):
    if app.printer.is_installed() and not app.printer.is_ready():
        app.count.publish_mqtt_counters('MissPaper')

@pibooth.hookimpl
def pibooth_cleanup(app):
    if isinstance(app.count, MqttCounters):
        app.count.disconnect()
