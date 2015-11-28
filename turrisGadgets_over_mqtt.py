#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import serial
import time
import re
import random
from threading import Timer
from socket import error as socket_error

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.3"
__email__ = "rene@renekliment.cz"

############
#  CONFIG  #
############

prefix = "turrisGadgets/"

# dict keys are serial numbers
devices = {
	'00000001': {'product': 'RC-86K', 'mqttPath': 'remote1L'},
	'00000002': {'product': 'RC-86K', 'mqttPath': 'remote1R'},
	'00000003': {'product': 'RC-86K', 'mqttPath': 'remote2L'},
	'00000004': {'product': 'RC-86K', 'mqttPath': 'remote2R'},
	'00000005': {'product': 'JA-81M', 'mqttPath': 'hallway/maindoor'},
	'00000006': {'product': 'JA-83M', 'mqttPath': 'room/balconywindow'},
	'00000007': {'product': 'JA-83M', 'mqttPath': 'room/window'},
	'00000008': {'product': 'JA-83P', 'mqttPath': 'room/pir'},
	'00000009': {'product': 'JA-83P', 'mqttPath': 'hallway/pir'},
	'00000010': {'product': 'JA-85ST', 'mqttPath': 'livingroom/smokedetector'},
	'00000011': {'product': 'JA-82SH', 'mqttPath': 'livingroom/vault'},
	'00000012': {'product': 'JA-80L', 'mqttPath': 'siren'},
	'00000013': {'product': 'TP-82N', 'mqttPath': 'thermostat'},
	'00000014': {'product': 'AC-88', 'mqttPath': 'room/socket/speakers', 'stateLabel': 'PGY'},
	'00000015': {'product': 'AC-88', 'mqttPath': 'room/socket/lamp', 'stateLabel': 'PGX'}
}

mqttConfig = {
	'server':	'localhost',
	'port':		1883,
	'client_id':'turrisGadgets',
	'user':		'', # leave empty for anonymous access
	'password': ''
}

################
#  To be done  #
################
#TODO: handle receiving the same message multiple times from a sensor (when it is desired)
################################################################################################

states = {
	'PGX': '0',
	'PGY': '0',
	'ALARM': '0',
	'BEEP': 'NONE'
}

statesToBe = None
stateRepeatsLeft = 0

ser = serial.Serial('/dev/ttyUSB0', 57600, timeout=None)
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
	mqttc.subscribe(prefix + '#', 2)
	
cmd('WHO AM I?')

# gets the system in a defined state
sendState({})

mqttc = mqtt.Client(client_id=mqttConfig['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (mqttConfig['user'] != ''):
	mqttc.username_pw_set(mqttConfig['user'], mqttConfig['password'])

mqttc.connect(mqttConfig['server'], mqttConfig['port'], 60)

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

			mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lastseen', time.time(), 2, True);

			if (product == 'RC-86K'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], 2, True);

				if (chunks[0] == 'PANIC'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], 'panic', 2, False);
				else:
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[0][-1:], 2, False);

			elif (product == 'JA-81M') or (product == 'JA-83M'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], 2, True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], 2, True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], chunks[2][-1:], 2, True);

			elif (product == 'JA-83P'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], 2, True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], 2, True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', 2, False);

			elif (product == 'JA-85ST'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], 2, True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], 2, True);
				elif (chunks[0] == 'DEFECT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/defect', chunks[2][-1:], 2, True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', 2, False);
				elif (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', 2, False);

			elif (product == 'JA-82SH'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', chunks[1][-1:], 2, True);

				if (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', chunks[2][-1:], 2, True);
				elif (chunks[0] == 'SENSOR'):
					mqttc.publish(prefix + devices[serial]['mqttPath'], '', 2, False);

			elif (product == 'JA-80L'):
				chunks = message.split(' ')

				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/blackout', message[-1:], 2, True);

				if (chunks[0] == 'BUTTON'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/button', '', 2, False);
				elif (chunks[0] == 'TAMPER'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/tamper', '', 2, False);

			elif (product == 'TP-82N'):
				mqttc.publish(prefix + devices[serial]['mqttPath'] + '/lowbattery', message[-1:], 2, True);

				if (message[0:3] == 'SET'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/set', message[4:8], 2, True);
				elif (message[0:3] == 'INT'):
					mqttc.publish(prefix + devices[serial]['mqttPath'] + '/measured', message[4:8], 2, True);

			elif (product == 'AC-88'):
				states[devices[serial]['stateLabel']] = message[-1:]
				mqttc.publish(prefix + devices[serial]['mqttPath'], message[-1:], 2, True);

	time.sleep(0.1)