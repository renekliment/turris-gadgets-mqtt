#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""MQTT gateway for Turris Gadgets dongle"""

import argparse
import logging
import os
import time

from socket import error as socket_error

import serial
import yaml

import paho.mqtt.client as mqtt

from turris_gadgets.controller import TurrisGadgetsController

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.5"
__email__ = "rene@renekliment.cz"

DEFAULT_CONFIG_FILE = os.path.join(
	os.path.dirname(os.path.abspath(__file__)),
	'config.yaml',
)

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument(
	'--config',
	default=DEFAULT_CONFIG_FILE,
	help='config file (default: {script_directory}/config.yaml)',
)

args = arg_parser.parse_args()

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

with open(args.config, 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']

auto_messages = {}
if ('automessages' in config) and (config['automessages']):
	auto_messages = config['automessages']

dongle_serial = serial.Serial(config['serial']['port'], config['serial']['baudrate'], timeout=config['serial']['timeout'])
time.sleep(1)


def send_to_serial(command: str):
	"""Send command to the dongle"""
	logger.debug("# TO: %s", command)

	try:
		command = bytes("\x1B" + command + "\n")
	except TypeError:
		command = bytes("\x1B" + command + "\n", "utf-8")

	dongle_serial.write(command)

def on_mqtt_message(client, obj, msg): # pylint: disable=unused-argument,missing-docstring

	for device_serial in config['devices']:
		if (msg.topic.startswith(prefix + config['devices'][device_serial]['mqttPath'])):
			payload = msg.payload.decode()
			turris_gadgets.handle_from_mqtt(device_serial, msg.topic, payload)
			break


def on_mqtt_disconnect(client, userdata, rc): # pylint: disable=unused-argument,missing-docstring,invalid-name

	logger.info("# Called on_disconnect!")
	while True:
		try:
			if (client.reconnect() == 0):
				logger.info("# Reconnected successfully.")
				break
		except socket_error:
			pass

		time.sleep(1)


def on_mqtt_connect(client, userdata, flags, rc): # pylint: disable=unused-argument,missing-docstring,invalid-name
	client.subscribe(prefix + '#', config['mqtt']['default_qos'])

	if ('on_connect' in auto_messages):
		for item in auto_messages['on_connect']:
			client.publish(prefix + item['topic'], item['payload'], item['qos'], item['retain'])


mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if ('last_will' in auto_messages):
	mqttc.will_set(prefix + auto_messages['last_will']['topic'], auto_messages['last_will']['payload'],
				   auto_messages['last_will']['qos'], auto_messages['last_will']['retain'])

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

turris_gadgets = TurrisGadgetsController(
	config['devices'],
	int(config['mqtt']['default_qos']),
	prefix,
	send_to_serial,
	mqttc.publish
)

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])
mqttc.loop_start()

while True:
	while dongle_serial.inWaiting():
		line = dongle_serial.readline().decode('ascii', errors='ignore').strip()
		if not line:
			break

		logger.debug("# FR: %s", line)

		turris_gadgets.handle_from_serial(line)

	time.sleep(0.1)
