#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt

__author__ = "René Kliment"
__license__ = "DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE, Version 2, December 2004"
__version__ = "0.1"
__email__ = "rene@renekliment.cz"

############
#  CONFIG  #
############

prefix = 'turrisGadgets/'

mqttConfig = {
	'server':	'localhost',
	'port':		1883,
	'client_id':'remote_control_socket',
	'user':		'', # leave empty for anonymous access
	'password': ''
}

#####################################################################################
def on_mqtt_message(mqttc, obj, msg):
	
	# This first condition is not needed since we **only subscribe to this single topic** (see the mqttc.subscribe call below),
	# however if we were to enhance this script's capabilities and subscribed to multiple topics,
	# this is here to remind us to filter the messages. 
	if (msg.topic == prefix + 'remote1R') and (msg.payload in ['0', '1']):
		mqttc.publish(prefix + 'room/socket/lamp/control', msg.payload, 2, False);

# MQTT client
mqttc = mqtt.Client(client_id=mqttConfig['client_id'], protocol=3)
mqttc.on_message = on_mqtt_message

if (mqttConfig['user'] != ''):
	mqttc.username_pw_set(mqttConfig['user'], mqttConfig['password'])

mqttc.connect(mqttConfig['server'], mqttConfig['port'], 60)
mqttc.subscribe(prefix + 'remote1R', 2)

mqttc.loop_forever()