#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""MQTT gateway for Turris Gadgets dongle"""

import logging
import os
import time
import random
import re
from threading import Timer
from socket import error as socket_error

import serial
import yaml

import paho.mqtt.client as mqtt

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.5"
__email__ = "rene@renekliment.cz"

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

script_directory = os.path.dirname(os.path.abspath(__file__)) + '/'
with open(script_directory + "config.yaml", 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']
devices = config['devices']

auto_messages = {}
if ('automessages' in config) and (config['automessages']):
	auto_messages = config['automessages']

states = {
	'PGX': '0',
	'PGY': '0',
	'ALARM': '0',
	'BEEP': 'NONE',
}

statesToBe = None
stateRepeatsLeft = 0

dongle_serial = serial.Serial(config['serial']['port'], config['serial']['baudrate'], timeout=config['serial']['timeout'])
time.sleep(1)


def send_command(command):
	"""Send command to the dongle"""
	logger.debug("# TO: %s", command)

	try:
		command = bytes("\x1B" + command + "\n")
	except TypeError:
		command = bytes("\x1B" + command + "\n", "utf-8")

	dongle_serial.write(command)


def send_state(new_states):
	"""Send state message to the dongle"""
	global statesToBe, stateRepeatsLeft # pylint: disable=global-statement

	if (statesToBe is None):
		statesToBe = states.copy()
		stateRepeatsLeft = 3

	if (new_states):
		stateRepeatsLeft = 3

	statesToBe.update(new_states)

	send_command('TX ENROLL:0 PGX:%s PGY:%s ALARM:%s BEEP:%s'
		% (statesToBe['PGX'], statesToBe['PGY'], statesToBe['ALARM'], statesToBe['BEEP']))

	stateRepeatsLeft -= 1

	if (stateRepeatsLeft == 0):
		statesToBe = None


def on_mqtt_message(client, obj, msg): # pylint: disable=unused-argument,missing-docstring

	for device in devices:

		if (msg.topic.startswith(prefix + devices[device]['mqttPath'])):

			payload = msg.payload.decode()

			if (devices[device]['product'] == 'AC-88'):
				if (msg.topic == prefix + devices[device]['mqttPath'] + '/control') and (payload in ["0", "1"]):
					send_state({devices[device]['stateLabel']: payload})

			elif (devices[device]['product'] == 'JA-80L'):
				if (msg.topic == prefix + devices[device]['mqttPath'] + '/alarm/control') and (payload in ["0", "1"]):
					states['ALARM'] = payload
					send_state({})

				elif (msg.topic == prefix + devices[device]['mqttPath'] + '/beep/control') and (payload in ["none", "slow", "fast"]):
					states['BEEP'] = payload.upper()
					send_state({})

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

send_command('WHO AM I?')

# gets the system in a defined state
send_state({})

mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if ('last_will' in auto_messages):
	mqttc.will_set(prefix + auto_messages['last_will']['topic'], auto_messages['last_will']['payload'],
				   auto_messages['last_will']['qos'], auto_messages['last_will']['retain'])

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])

mqttc.loop_start()

while True:

	line = ''

	while dongle_serial.inWaiting():
		line = dongle_serial.readline().decode('ascii', errors='ignore').strip()
		if not line:
			break

		logger.debug("# FR: %s", line)

		if (line == 'OK'):
			if (stateRepeatsLeft > 0) and (statesToBe is not None):

				interval = 0.2 + random.random() * 0.3
				Timer(interval, send_state, [{}]).start()

		if (line == 'OK') or (line == 'ERROR') or (line.startswith('TURRIS')):
			break

		m = re.match("\[(\d+)\] ([a-zA-Z0-9_-]+) (.+)", line) # pylint: disable=anomalous-backslash-in-string
		serial = m.group(1)
		product = m.group(2)
		message = m.group(3)

		if (serial in devices.keys()):

			mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lastseen', time.time(), config['mqtt']['default_qos'], True)

			if (product == 'RC-86K'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'PANIC'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], 'panic', config['mqtt']['default_qos'], False)
				else:
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[0][-1:], config['mqtt']['default_qos'], False)

			elif (product in ('JA-81M', 'JA-83M')):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True)
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[2][-1:], config['mqtt']['default_qos'], True)

			elif (product == 'JA-83P'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True)
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False)

			elif (product == 'JA-85ST'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True)
				elif (chunks[0] == 'DEFECT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/defect', chunks[2][-1:], config['mqtt']['default_qos'], True)
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False)
				elif (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', config['mqtt']['default_qos'], False)

			elif (product == 'JA-82SH'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True)
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False)

			elif (product == 'JA-80L'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/blackout', message[-1:], config['mqtt']['default_qos'], True)

				if (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', config['mqtt']['default_qos'], False)
				elif (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', '', config['mqtt']['default_qos'], False)

			elif (product == 'TP-82N'):
				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', message[-1:], config['mqtt']['default_qos'], True)

				if (message[0:3] == 'SET'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/set', message[4:8], config['mqtt']['default_qos'], True)
				elif (message[0:3] == 'INT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/measured', message[4:8], config['mqtt']['default_qos'], True)

			elif (product == 'AC-88'):
				states[devices[serial]['stateLabel']] = message[-1:]
				mqttc.publish(prefix + devices[serial]['mqttPath'], message[-1:], config['mqtt']['default_qos'], True)

	time.sleep(0.1)
