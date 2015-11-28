#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import mpd
import paho.mqtt.client as mqtt
import time
from socket import error as socket_error

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.2"
__email__ = "rene@renekliment.cz"

############
#  CONFIG  #
############

prefix = 'turrisGadgets/'

mpdConfig = {
	'server':	'localhost',
	'port':		6600,
	'password': '' # leave empty for anonymous access
}

mqttConfig = {
	'server':	'localhost',
	'port':		1883,
	'client_id':'mpd_volume_thermostat',
	'user':		'', # leave empty for anonymous access
	'password': ''
}

#####################################################################################
def on_mqtt_message(mqttc, obj, msg):

	# This condition is not needed since we **only subscribe to this single topic** (see the mqttc.subscribe call below),
	# however if we were to enhance this script's capabilities and subscribed to multiple topics,
	# this is here to remind us to filter the messages. 
	if (msg.topic == prefix + 'thermostat/set'):
		mpdc.setvol(int( 
				((float(msg.payload) - 6) / 34) * 100
		));	
		
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
	mqttc.subscribe(prefix + 'thermostat/set', 2)
		
# MPD client
mpdc = mpd.MPDClient(use_unicode=True)
mpdc.connect(mpdConfig['server'], mpdConfig['port'])

if (mpdConfig['password'] != ''):
	mpdc.password(mpdConfig['password'])

# MQTT client
mqttc = mqtt.Client(client_id=mqttConfig['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message
mqttc.on_disconnect = on_mqtt_disconnect
mqttc.on_connect = on_mqtt_connect

if (mqttConfig['user'] != ''):
	mqttc.username_pw_set(mqttConfig['user'], mqttConfig['password'])

mqttc.connect(mqttConfig['server'], mqttConfig['port'], 60)

mqttc.loop_start()

while True:
	mpdc.ping()
	time.sleep(30)