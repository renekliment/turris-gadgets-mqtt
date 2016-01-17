#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import yaml
import paho.mqtt.client as mqtt
import serial
import time
import re
import random
from threading import Timer
from socket import error as socket_error

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.4"
__email__ = "rene@renekliment.cz"

#TODO: handle receiving the same message multiple times from a sensor (when it is desired)


swd = os.path.dirname(os.path.abspath(__file__)) + '/'
with open(swd + "config.yaml", 'r') as f:
	config = yaml.load(f)

prefix = config['mqtt']['prefix']
devices = config['devices']

states = {
	'PGX': '0',
	'PGY': '0',
	'ALARM': '0',
	'BEEP': 'NONE'
}

statesToBe = None
stateRepeatsLeft = 0

ser = serial.Serial(config['serial']['port'], config['serial']['baudrate'], timeout=config['serial']['timeout'])
time.sleep(1)

def cmd(line):
	print("# TO: " + line)
	ser.write("\x1B" + line + "\n")

def sendState(newStates):
	global statesToBe, stateRepeatsLeft

	if (statesToBe is None):
		statesToBe = states.copy()
		stateRepeatsLeft = 3

	if (newStates):
		stateRepeatsLeft = 3

	statesToBe.update(newStates)

	cmd('TX ENROLL:0 PGX:' + statesToBe['PGX'] + ' PGY:' + statesToBe['PGY'] + ' ALARM:' + statesToBe['ALARM'] + ' BEEP:' + statesToBe['BEEP'])

	stateRepeatsLeft -= 1

	if (stateRepeatsLeft == 0):
		statesToBe = None

def on_mqtt_message(mqttc, obj, msg):

	for device in devices:

		if (msg.topic.startswith(prefix + devices[device]['mqttPath'])):

			if (devices[device]['product'] == 'AC-88'):
				if (msg.topic == prefix + devices[device]['mqttPath'] + '/control') and (msg.payload in ["0", "1"]):
					sendState({devices[device]['stateLabel']: msg.payload})

			elif (devices[device]['product'] == 'JA-80L'):
				if (msg.topic == prefix + devices[device]['mqttPath'] + '/alarm/control') and (msg.payload in ["0", "1"]):
					states['ALARM'] = msg.payload
					sendState({})

				elif (msg.topic == prefix + devices[device]['mqttPath'] + '/beep/control') and (msg.payload in ["none", "slow", "fast"]):
					states['BEEP'] = msg.payload.upper()
					sendState({})

			break

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
	mqttc.subscribe(prefix + '#', config['mqtt']['default_qos'])
	
cmd('WHO AM I?')

# gets the system in a defined state
sendState({})

mqttc = mqtt.Client(client_id=config['mqtt']['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (config['mqtt']['user'] != ''):
	mqttc.username_pw_set(config['mqtt']['user'], config['mqtt']['password'])

mqttc.connect(config['mqtt']['server'], config['mqtt']['port'], config['mqtt']['timeout'])

mqttc.loop_start()

while True:

	while ( ser.inWaiting() ):
		line = ser.readline().strip().strip('\n').strip('\t')
		if (line == ''):
			break

		print("# FR: " + line)

		if (line == 'OK'):
			if (stateRepeatsLeft > 0) and (statesToBe is not None):

				interval = 0.2 + random.random() * 0.3;
				Timer(interval, sendState, [{}]).start()

		if (line == 'OK') or (line == 'ERROR') or (line.startswith('TURRIS')):
			break

		m = re.match("\[(\d+)\] ([a-zA-Z0-9_-]+) (.+)", line)
		serial = m.group(1)
		product = m.group(2)
		message = m.group(3)

		if (devices.has_key(serial)):

			mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lastseen', time.time(), config['mqtt']['default_qos'], True);

			if (product == 'RC-86K'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'PANIC'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], 'panic', config['mqtt']['default_qos'], False);
				else:
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[0][-1:], config['mqtt']['default_qos'], False);

			elif (product == 'JA-81M') or (product == 'JA-83M'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[2][-1:], config['mqtt']['default_qos'], True);

			elif (product == 'JA-83P'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False);

			elif (product == 'JA-85ST'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True);
				elif (chunks[0] == 'DEFECT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/defect', chunks[2][-1:], config['mqtt']['default_qos'], True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False);
				elif (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', config['mqtt']['default_qos'], False);

			elif (product == 'JA-82SH'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], config['mqtt']['default_qos'], True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', config['mqtt']['default_qos'], False);

			elif (product == 'JA-80L'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/blackout', message[-1:], config['mqtt']['default_qos'], True);

				if (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', config['mqtt']['default_qos'], False);
				elif (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', '', config['mqtt']['default_qos'], False);

			elif (product == 'TP-82N'):
				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', message[-1:], config['mqtt']['default_qos'], True);

				if (message[0:3] == 'SET'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/set', message[4:8], config['mqtt']['default_qos'], True);
				elif (message[0:3] == 'INT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/measured', message[4:8], config['mqtt']['default_qos'], True);

			elif (product == 'AC-88'):
				states[devices[serial]['stateLabel']] = message[-1:]
				mqttc.publish(prefix + devices[serial]['mqttPath'], message[-1:], config['mqtt']['default_qos'], True);

	time.sleep(0.1)