#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import mpd
import paho.mqtt.client as mqtt

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.1"
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
		
# MPD client
mpdc = mpd.MPDClient(use_unicode=True)
mpdc.connect(mpdConfig['server'], mpdConfig['port'])

if (mpdConfig['password'] != ''):
	mpdc.password(mpdConfig['password'])

# MQTT client
mqttc = mqtt.Client(client_id=mqttConfig['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message

if (mqttConfig['user'] != ''):
	mqttc.username_pw_set(mqttConfig['user'], mqttConfig['password'])

mqttc.connect(mqttConfig['server'], mqttConfig['port'], 60)
mqttc.subscribe(prefix + 'thermostat/set', 2)

mqttc.loop_forever()