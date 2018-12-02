#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Remote controlling a socket with a remote control

Demo for the Turris Gadgets MQTT gateway
"""

import logging
import os
import time
from socket import error as socket_error

import yaml
import paho.mqtt.client as mqtt

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.4"
__email__ = "rene@renekliment.cz"

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

swd = os.path.dirname(os.path.abspath(__file__)) + '/'
with open(swd + "config.demo_remote_control_socket.yaml", 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']


def on_mqtt_message(client, obj, msg): # pylint: disable=unused-argument,missing-docstring

	# This first condition is not needed since we **only subscribe to this single topic** (see the mqttc.subscribe call below),
	# however if we were to enhance this script's capabilities and subscribed to multiple topics,
	# this is here to remind us to filter the messages.
	if (msg.topic == prefix + 'remote1R') and (msg.payload in ['0', '1']):
		client.publish(prefix + 'room/socket/lamp/control', msg.payload, config['mqtt']['default_qos'], False)


def on_mqtt_disconnect(client, userdata, rc): # pylint: disable=unused-argument,missing-docstring,invalid-name

	logging.info("Called on_disconnect!")
	while True:
		try:
			if (client.reconnect() == 0):
				logging.info("Reconnected successfully.")
				break
		except socket_error:
			pass

		time.sleep(1)


def on_mqtt_connect(client, userdata, flags, rc): # pylint: disable=unused-argument,missing-docstring,invalid-name
	client.subscribe(prefix + 'remote1R', config['mqtt']['default_qos'])

# MQTT client
mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])

mqttc.loop_forever()
