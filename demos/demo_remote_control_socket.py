#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import yaml
import paho.mqtt.client as mqtt
import time
from socket import error as socket_error

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.3"
__email__ = "rene@renekliment.cz"

swd = os.path.dirname(os.path.abspath(__file__)) + '/'
with open(swd + "config.demo_remote_control_socket.yaml", 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']

def on_mqtt_message(mqttc, obj, msg):
	
	# This first condition is not needed since we **only subscribe to this single topic** (see the mqttc.subscribe call below),
	# however if we were to enhance this script's capabilities and subscribed to multiple topics,
	# this is here to remind us to filter the messages. 
	if (msg.topic == prefix + 'remote1R') and (msg.payload in ['0', '1']):
		mqttc.publish(prefix + 'room/socket/lamp/control', msg.payload, config['mqtt']['default_qos'], False);

def on_mqtt_disconnect(mqttc, userdata, rc):

	print("# Called on_disconnect!")
	while True:
		try:
			if (mqttc.reconnect() == 0):
				print("# Reconnected successfully.")
				break
		except socket_error:
			pass

		time.sleep(1)

def on_mqtt_connect(mqttc, userdata, flags, rc):
	mqttc.subscribe(prefix + 'remote1R', config['mqtt']['default_qos'])

# MQTT client
mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])

mqttc.loop_forever()