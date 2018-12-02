#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Controlling MPD volume with a thermostat

Demo for the Turris Gadgets MQTT gateway
"""

import logging
import os
import time
from socket import error as socket_error

import yaml
import paho.mqtt.client as mqtt
import mpd # pylint: disable=import-error

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.4"
__email__ = "rene@renekliment.cz"

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

swd = os.path.dirname(os.path.abspath(__file__)) + '/'
with open(swd + "config.demo_mpd_volume_thermostat.yaml", 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']


def on_mqtt_message(client, obj, msg): # pylint: disable=unused-argument,missing-docstring

	# This condition is not needed since we **only subscribe to this single topic** (see the mqttc.subscribe call below),
	# however if we were to enhance this script's capabilities and subscribed to multiple topics,
	# this is here to remind us to filter the messages.
	if (msg.topic == prefix + 'thermostat/set'):
		volume = int(
				((float(msg.payload) - 6) / 34) * 100
		)
		mpdc.setvol(volume) # pylint: disable=no-member


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
	client.subscribe(prefix + 'thermostat/set', config['mqtt']['default_qos'])

# MPD client
mpdc = mpd.MPDClient(use_unicode=True)
mpdc.connect(config['mpd']['server'], config['mpd']['port'])

if (config['mpd']['password'] != ''):
	mpdc.password(config['mpd']['password']) # pylint: disable=no-member

# MQTT client
mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])

mqttc.loop_start()

while True:
	mpdc.ping() # pylint: disable=no-member
	time.sleep(30)
