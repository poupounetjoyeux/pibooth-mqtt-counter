# pibooth-mqtt-counter plugin
Provide a way to send counters on an MQTT broker

This can be used for example to display the current number of taken photos on a led matrix display

### Installation
To install this plugin, you can simply use pip. pibooth will automatically enable discover and enable it
```
pip install git+https://github.com/poupounetjoyeux/pibooth-mqtt-counter.git@v1.0.5
```

### Configuration
This plugin append a new **[MQTT]** section

**All options are optional**
```
[MQTT]
# The MQTT broker host. Default is localhost
broker_host = localhost

# The MQTT broker port. Default is 1883
broker_port = 1883

# The MQTT username and password to connect to the borker
credentials = ('username', 'password')

# The MQTT client_id for the photobooth. Default is PiBooth
client_id = PiBooth

# The MQTT topic on which you want to publish/subscribe. Default is PiBooth meaning counters will be published over PiBooth/counters and reset events will be subscribed to PiBooth/reset
# Reset payload must contains 'true' (case insensitive)
topic = PiBooth
```

### Thanks
Thanks to the [pibooth](https://github.com/pibooth/pibooth) team that make a really great and amazing job!

