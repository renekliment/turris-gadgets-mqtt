# pylint: disable=missing-docstring
import logging
import random
import re
import time
from threading import Timer
from typing import Callable

logging.basicConfig(format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class TurrisGadgetsController:
	"""Simple serial-MQTT bridge for Turris Gadgets"""
	states = {
		'PGX': '0',
		'PGY': '0',
		'ALARM': '0',
		'BEEP': 'NONE',
	}

	statesToBe = None
	stateRepeatsLeft = 0

	def __init__(
			self,
			devices: dict,
			mqtt_default_qos: int,
			mqtt_prefix: str,
			send_to_serial: Callable[[str], None],
			send_to_mqtt: Callable[[str, str, int, bool], None]
	):
		self.devices = devices
		self.mqtt_default_qos = mqtt_default_qos
		self.mqtt_prefix = mqtt_prefix

		self.send_to_serial = send_to_serial
		self.send_to_mqtt = send_to_mqtt

		self.send_to_serial('WHO AM I?')

		# gets the system in a defined state
		self.send_state({})

	def send_state(self, new_states: dict):
		"""Send state message to the dongle"""

		if (self.statesToBe is None):
			self.statesToBe = self.states.copy()
			self.stateRepeatsLeft = 3

		if (new_states):
			self.stateRepeatsLeft = 3

		self.statesToBe.update(new_states)

		self.send_to_serial('TX ENROLL:0 PGX:%s PGY:%s ALARM:%s BEEP:%s'
					 % (self.statesToBe['PGX'], self.statesToBe['PGY'], self.statesToBe['ALARM'], self.statesToBe['BEEP']))

		self.stateRepeatsLeft -= 1

		if (self.stateRepeatsLeft == 0):
			self.statesToBe = None

	def handle_from_mqtt(self, serial: str, topic: str, payload: str):  # pylint: disable=missing-docstring
		product = self.devices[serial]['product']
		device_mqtt_path = self.mqtt_prefix + self.devices[serial]['mqttPath']

		if (product == 'AC-88'):
			if (topic == device_mqtt_path + '/control') and (payload in ["0", "1"]):
				self.send_state({
					self.devices[serial]['stateLabel']: payload
				})

		elif (product == 'JA-80L'):
			if (topic == device_mqtt_path + '/alarm/control') and (payload in ["0", "1"]):
				self.states['ALARM'] = payload
				self.send_state({})

			elif (topic == device_mqtt_path + '/beep/control') and (payload in ["none", "slow", "fast"]):
				self.states['BEEP'] = payload.upper()
				self.send_state({})

	def handle_from_serial(self, line: str):  # pylint: disable=missing-docstring
		if (line == 'OK'):
			if (self.stateRepeatsLeft > 0) and (self.statesToBe is not None):

				interval = 0.2 + random.random() * 0.3
				Timer(interval, self.send_state, [{}]).start()

		if (line == 'OK') or (line == 'ERROR') or (line.startswith('TURRIS')):
			return

		m = re.match("\[(\d+)\] ([a-zA-Z0-9_-]+) (.+)", line)  # pylint: disable=anomalous-backslash-in-string
		serial = m.group(1)
		product = m.group(2)
		message = m.group(3)

		if (serial not in self.devices.keys()):
			logger.warning("# Serial number %s not found in the config!", serial)
			return

		if self.devices[serial]['product'] != product:
			logger.warning("# Serial number (%s) / product (%s) mismatch!", serial, product)
			return

		self.process_device_message(serial, message)

	def process_device_message(self, serial: str, message: str):  # pylint: disable=too-many-branches,too-many-statements,missing-docstring
		product = self.devices[serial]['product']
		device_mqtt_path = self.mqtt_prefix + self.devices[serial]['mqttPath']
		default_qos = self.mqtt_default_qos

		self.send_to_mqtt(device_mqtt_path + '/lastseen', str(time.time()), default_qos, True)

		if (product == 'RC-86K'):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/lowbattery', chunks[1][-1:], default_qos, True)

			if (chunks[0] == 'PANIC'):
				self.send_to_mqtt(device_mqtt_path, 'panic', default_qos, False)
			else:
				self.send_to_mqtt(device_mqtt_path, chunks[0][-1:], default_qos, False)

		elif (product in ('JA-81M', 'JA-83M')):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/lowbattery', chunks[1][-1:], default_qos, True)

			if (chunks[0] == 'TAMPER'):
				self.send_to_mqtt(device_mqtt_path + '/tamper', chunks[2][-1:], default_qos, True)
			elif (chunks[0] == 'SENSOR'):
				self.send_to_mqtt(device_mqtt_path, chunks[2][-1:], default_qos, True)

		elif (product == 'JA-83P'):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/lowbattery', chunks[1][-1:], default_qos, True)

			if (chunks[0] == 'TAMPER'):
				self.send_to_mqtt(device_mqtt_path + '/tamper', chunks[2][-1:], default_qos, True)
			elif (chunks[0] == 'SENSOR'):
				self.send_to_mqtt(device_mqtt_path, '', default_qos, False)

		elif (product == 'JA-85ST'):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/lowbattery', chunks[1][-1:], default_qos, True)

			if (chunks[0] == 'TAMPER'):
				self.send_to_mqtt(device_mqtt_path + '/tamper', chunks[2][-1:], default_qos, True)
			elif (chunks[0] == 'DEFECT'):
				self.send_to_mqtt(device_mqtt_path + '/defect', chunks[2][-1:], default_qos, True)
			elif (chunks[0] == 'SENSOR'):
				self.send_to_mqtt(device_mqtt_path, '', default_qos, False)
			elif (chunks[0] == 'BUTTON'):
				self.send_to_mqtt(device_mqtt_path + '/button', '', default_qos, False)

		elif (product == 'JA-82SH'):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/lowbattery', chunks[1][-1:], default_qos, True)

			if (chunks[0] == 'TAMPER'):
				self.send_to_mqtt(device_mqtt_path + '/tamper', chunks[2][-1:], default_qos, True)
			elif (chunks[0] == 'SENSOR'):
				self.send_to_mqtt(device_mqtt_path, '', default_qos, False)

		elif (product == 'JA-80L'):
			chunks = message.split(' ')

			self.send_to_mqtt(device_mqtt_path + '/blackout', message[-1:], default_qos, True)

			if (chunks[0] == 'BUTTON'):
				self.send_to_mqtt(device_mqtt_path + '/button', '', default_qos, False)
			elif (chunks[0] == 'TAMPER'):
				self.send_to_mqtt(device_mqtt_path + '/tamper', '', default_qos, False)

		elif (product == 'TP-82N'):
			self.send_to_mqtt(device_mqtt_path + '/lowbattery', message[-1:], default_qos, True)

			if (message[0:3] == 'SET'):
				self.send_to_mqtt(device_mqtt_path + '/set', message[4:8], default_qos, True)
			elif (message[0:3] == 'INT'):
				self.send_to_mqtt(device_mqtt_path + '/measured', message[4:8], default_qos, True)

		elif (product == 'AC-88'):
			self.states[self.devices[serial]['stateLabel']] = message[-1:]
			self.send_to_mqtt(device_mqtt_path, message[-1:], default_qos, True)
