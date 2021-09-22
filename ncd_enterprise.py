from digi.xbee.devices import DigiMeshDevice
from digi.xbee.devices import RemoteDigiMeshDevice
from digi.xbee.models.address import XBee64BitAddress
from digi.xbee.packets.base import DictKeys
from digi.xbee.packets.common import ATCommResponsePacket
from functools import reduce
import time

class NCDEnterprise:
    def __init__(self, serial_port, baud_rate, callback, kwargs = {}):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.sensor_types = sensor_types()
        self.payload_type = {
            '122': 'power_up',
            '124': 'config_ack',
            '125': 'config_error',
            '127': 'sensor_data'
        }
        self.data = {}
        self.device = DigiMeshDevice(serial_port, baud_rate)
        self.device.open()
        self.callback = callback
        self.device.add_packet_received_callback(self.parse)
        self.error_callback = None
        if kwargs.get('error_handler'):
            self.error_callback = kwargs.get('error_handler')
        self.mems_buffer = {}

    def send_data_to_address(self, address, data):
        remote_device = RemoteDigiMeshDevice(self.device, XBee64BitAddress.from_hex_string(address))
        self.device.send_data(remote_device, data)

    def parse(self, xbee_packet):
        if not isinstance(xbee_packet, ATCommResponsePacket):
            data = xbee_packet.rf_data
            packet_type = self.payload_type[str(data[0])]
            # if the length is exactly 180, assume it is a mems data packet
            if(len(data) == 180):
                self.buffer_mems(data[1:], xbee_packet.x64bit_source_addr)
                return

            type = self.payload_type[str(data[0])]
            if(callable(getattr(self, packet_type))):
                getattr(self, packet_type)(data[1:], xbee_packet.x64bit_source_addr)
        else:
            print(xbee_packet)

    def buffer_mems(self, payload, source_address):
        source_address = str(source_address)
        if not self.mems_buffer.get(source_address, False):
            self.mems_buffer[source_address] = {}


        # If there is an ongoing error, process it. This is primarily to reduce
        # multiple instances of data corruption errors for the same dataset from
        # the sensor
        # If the dict has an error key
        if self.mems_buffer.get(source_address).get('timeout_exception_start'):
            # self.mems_buffer[source_address][payload[1]] = payload[5:]
            # if 500 millis have passed or this is a last packet (packet 12)
            if (self.get_current_millis() - self.mems_buffer.get(source_address).get('timeout_exception_start')) > 500 or payload[1] == 12:
                self.mems_buffer[source_address][payload[1]] = payload[5:]
                # set error
                self.parse_error_callback(self.mems_buffer.get(source_address))
                # clear buffer
                self.mems_buffer[source_address] = {}
                # if the current payload is not a new dataset, do not process further
                if payload[1] != 1:
                    return

        if payload[1] not in self.mems_buffer.get(source_address):
            if len(self.mems_buffer.get(source_address)) == (int(payload[1]) -1):
                # packet has been shifted left one, therefore data will start at byte 5.
                self.mems_buffer[source_address][payload[1]] = payload[5:]
            else:
                self.mems_buffer[source_address][payload[1]] = payload[5:]
                self.mems_buffer[source_address]['timeout_exception_start'] = self.get_current_millis()
                return
        else:
            print('Duplicate keys error reported in V2 Mems Buffer')

        if(len(self.mems_buffer.get(source_address)) == 12):
            # packet from intercept has first byte trimmed. Shift expected position left.
            # i.e. node_id is byte 0 instead of documented one.
            self.parse_mems(self.mems_buffer.get(source_address), source_address, payload)
            self.mems_buffer[source_address] = {}

    # TODO configuration commands put on hiatus. Need to import struct lib to ensure
    # packet compatibility. AKA sleep_time needs to be 3 bytes, if a single int is passed
    # it won't be. extensive testing needed.
    # def sensor_set_node_id_sleep(self, target_address, node_id, sleep_time, log = True):
    #     node_id = bytearray(node_id)
    #     sleep_time = bytearray(node_id)
    #     self.send_data_to_address(target_address, bytearray.fromhex('f702000000')+node_id+sleep_time)

    def parse_error_callback(self, message):
        if(callable(self.error_callback)):
            self.error_callback(message)

    def get_current_millis(self):
        return int(round(time.time() * 1000))

    def parse_mems(self, mems_dict, source_address, last_payload):
        readings = 29
        bytes_in_single = 6
        reading_array = {}
        for index, packet in enumerate(mems_dict):
            packet_data = mems_dict.get(packet)
            packet_array = {}
            for reading in range(1, readings+1):
                if packet == 12 and reading >= 22:
                    break
                reading_array[((index*readings)+reading)] = packet_data[((reading-1)*(bytes_in_single)):(reading-1)*(bytes_in_single)+bytes_in_single]
        for sample in reading_array:
            sample_data = reading_array.get(sample)
            reading_array[sample] = {
                'rms_x': signInt(reduce(msbLsb, sample_data[0:2]), 16),
                'rms_y': signInt(reduce(msbLsb, sample_data[2:4]), 16),
                'rms_z': signInt(reduce(msbLsb, sample_data[4:6]), 16)
            }
        reading_array['temperature'] = msbLsb(last_payload[-6], last_payload[-5])
        parsed = {
            'nodeId': last_payload[0],
            'odr': last_payload[4],
            'firmware': last_payload[-4],
            'battery': msbLsb(last_payload[-3], last_payload[-2]) * 0.00322,
            'battery_percent': str(((msbLsb(last_payload[-3], last_payload[-2]) * 0.00322) - 1.3)/2.03*100) + "%",
            'counter': 'NA',
            'sensor_type_id': 40,
            'source_address': str(source_address),
            'sensor_type_string': 'Vibration Time Series',
            'sensor_data': reading_array
        }
        self.callback(parsed)

    def sensor_data(self, payload, source_address):
        parsed = {
            'nodeId': payload[0],
            'firmware': payload[1],
            'battery': msbLsb(payload[2], payload[3]) * 0.00322,
            'battery_percent': str(((msbLsb(payload[2], payload[3]) * 0.00322) - 1.3)/2.03*100) + "%",
            'counter': payload[4],
            'sensor_type_id': msbLsb(payload[5], payload[6]),
            'source_address': str(source_address),
        }
        try:
            if(parsed['sensor_type_id'] == 80):
                parsed['sensor_type_string'] = 'One Channel Vibration Plus'
                parsed['sensor_data'] = type80(payload, parsed, source_address)

            else:
                parsed['sensor_type_string'] = self.sensor_types[str(parsed['sensor_type_id'])]['name']
                parsed['sensor_data'] = self.sensor_types[str(parsed['sensor_type_id'])]['parse'](payload[8:])

        except:
            parsed['sensor_type_string'] = 'Unsupported Sensor'
            parsed['sensor_data'] = payload
            self.callback(parsed)
        self.callback(parsed)

    def power_up(self, payload, source_address):
        return {
            'nodeId': payload[0],
            'sensor_type': msbLsb(payload[2], payload[3]),
            'source_address': str(source_address)
        }

    def config_ack(self, payload, source_address):
        return {
            'nodeId': payload[0],
            'counter': payload[1],
            'sensor_type': msbLsb(payload[2], payload[3]),
            'source_address': str(source_address)
        }
    def stop(self):
        self.device.close()
    def start(self):
        self.device.start()
    def config_error(self, payload):
        errors = [
            'Unknown',
            'Invalid Command',
            'Sensor Type Mismatch',
            'Node ID Mismatch',
            'Apply change command failed',
            'Invalid API Packet Command Response Received After Apply Change Command',
            'Write command failed',
            'Invalid API Packet Command Response Received After Write Command',
            'Parameter Change Command Failed',
            'Invalid Parameter Change Command Response Received After Write Command',
            'Invalid/Incomplete Packet Received',
            'Unknown',
            'Unknown',
            'Unknown',
            'Unknown',
            'Invalid Parameter for Setup/Saving'
        ]
        return {
            'nodeId': payload[0],
            'sensor_type': msbLsb(payload[2], payload[3]),
            'error': payload[6],
            'error_message': errors[payload[6]],
            # last_sent: this.digi.lastSent
        }

def sensor_types():
    types = {
        # check
        '1': {
            'name': 'Temperature/Humidity',
            'parse':  lambda d : {
                'humidity': msbLsb(d[0], d[1])/100,
                'temperature': (signInt(msbLsb(d[2], d[3]), 16)/100)
            }
        },
        # check
        '2': {
            'name': '2 Channel Push Notification',
            'parse': lambda d :	{
                'input_1': d[0],
                'input_2': d[1]
            }
        },
        # check
        '3': {
            'name': 'ADC',
            'parse': lambda d :	{
                'input_1': msbLsb(d[0], d[1]),
                'input_2': msbLsb(d[2], d[3])
            }
        },
        # untested - altered
        '4': {
            'name': 'Thermocouple',
            'parse': lambda d :	{
                'temperature': signInt(reduce(msbLsb, d[0:4]), 32)/100
            }
        },
        # check
        '5': {
            'name': 'Gyro/Magneto/Temperature',
            'parse': lambda d :	{
                'accel_x': signInt(reduce(msbLsb, d[0:3]), 24)/100,
                'accel_y': signInt(reduce(msbLsb, d[3:6]), 24)/100,
                'accel_z': signInt(reduce(msbLsb, d[6:9]), 24)/100,
                'magneto_x': signInt(reduce(msbLsb, d[9:12]), 24)/100,
                'magneto_y': signInt(reduce(msbLsb, d[12:15]), 24)/100,
                'magneto_z': signInt(reduce(msbLsb, d[15:18]), 24)/100,
                'gyro_x': signInt(reduce(msbLsb, d[18:21]), 24),
                'gyro_y': signInt(reduce(msbLsb, d[21:24]), 24),
                'gyro_z': signInt(reduce(msbLsb, d[24:27]), 24),
                'temperature': signInt(msbLsb(d[27], d[28]), 16)
            }
       },
        # untested - altered
        '6': {
            'name': 'Temperature/Barometeric Pressure',
            'parse': lambda d :	{
                'temperature': signInt(msbLsb(d[0], d[1]), 16),
                'absolute_pressure': msbLsb(d[2], d[3])/1000,
                'relative_pressure': signInt(msbLsb(d[4], d[5]), 16)/1000,
                'altitude_change': signInt(msbLsb(d[6], d[7]), 16)/100
            }
        },
        #untested
        '7': {
			'name': 'Impact Detection',
			'parse': lambda d : {
				'acc_x1': signInt(reduce(msbLsb, d[0:2]), 16),
				'acc_x2': signInt(reduce(msbLsb, d[2:4]), 16),
				'acc_x': signInt(reduce(msbLsb, d[4:6]), 16),
				'acc_y1': signInt(reduce(msbLsb, d[6:8]), 16),
				'acc_y2': signInt(reduce(msbLsb, d[8:10]), 16),
				'acc_y': signInt(reduce(msbLsb, d[10:12]), 16),
				'acc_z1': signInt(reduce(msbLsb, d[12:14]), 16),
				'acc_z2': signInt(reduce(msbLsb, d[14:16]), 16),
				'acc_z': signInt(reduce(msbLsb, d[16:18]), 16),
				'temp_change': signInt(reduce(msbLsb, d[18:20]), 16)
            }
        },
        # check
        '8': {
            'name': 'Vibration',
            'parse': lambda d : {
                'rms_x': signInt(reduce(msbLsb, d[0:3]), 24)/100,
                'rms_y': signInt(reduce(msbLsb, d[3:6]), 24)/100,
                'rms_z': signInt(reduce(msbLsb, d[6:9]), 24)/100,
                'max_x': signInt(reduce(msbLsb, d[9:12]), 24)/100,
                'max_y': signInt(reduce(msbLsb, d[12:15]), 24)/100,
                'max_z': signInt(reduce(msbLsb, d[15:18]), 24)/100,
                'min_x': signInt(reduce(msbLsb, d[18:21]), 24)/100,
                'min_y': signInt(reduce(msbLsb, d[21:24]), 24)/100,
                'min_z': signInt(reduce(msbLsb, d[24:27]), 24)/100,
                'temperature': msbLsb(d[27], d[28])
            }
        },
        # untested
		'9': {
			'name': 'Proximity',
			'parse': lambda d :	{
				'proximity': msbLsb(d[0], d[1]),
				'lux': msbLsb(d[2], d[3]) * .25
			}
		},
        # check
        '10': {
            'name': 'Light',
            'parse': lambda d :	{
                'lux': reduce(msbLsb, d[0:3])
            }
        },
        # untested
		'12': {
			'name': '3-Channel Thermocouple',
            'parse': lambda d :	{
				'channel_1': signInt(reduce(msbLsb, d[0:4]), 32) / 100,
				'channel_2': signInt(reduce(msbLsb, d[4:8]), 32) / 100,
				'channel_3': signInt(reduce(msbLsb, d[8:12]), 32) / 100
			}
		},
        # untested
		'13': {
			'name': 'Current Monitor',
			'parse': lambda d :	{
				'amps': reduce(msbLsb, d[0:3])/1000
			}
		},
        # TODO - test out the double lambda, this seems super un-pythonic so
        # consider re-writing in the future.
        # could lead to poor compatibility
        # untested - extremely untested
		'14': {
			'name': '10-Bit 1-Channel 4-20mA',
			'parse': lambda d : (lambda adc=reduce(msbLsb, d[0:2]) : {
                'adc': adc,
				'mA': adc * 20 / 998
			})()
		},
        # TODO - test out the double lambda, this seems super un-pythonic so
        # consider re-writing in the future.
        # could lead to poor compatibility
        # untested - extremely untested
		'15': {
			'name': '10-Bit 1-Channel ADC',
			'parse': lambda d : (lambda adc=reduce(msbLsb, d[0:2]) : {
				'adc': adc,
				'voltage': adc * 0.00322265625
			})()
		},
        # TODO - test out the double lambda, this seems super un-pythonic so
        # consider re-writing in the future.
        # could lead to poor compatibility
        # untested - extremely untested
		'16': {
			'name': 'Soil Moisture Sensor',
			'parse': lambda d : (lambda adc1=reduce(msbLsb, d[0:2]), adc2=reduce(msbLsb, d[0:2]) : {
				'adc1': adc1,
				'adc2': adc2,
				'voltage1': adc1 * 0.00322265625,
				'voltage2': adc2 * 0.00322265625,
				'percentage': 100 if (adc > 870) else round(adc / 870 * 100)
			})()
		},
        # untested
		'17': {
			'name': '24-Bit AC Voltage Monitor',
			'parse': lambda d :	{
				'voltage': reduce(msbLsb, d[0:3]) / 32
			}
		},
        # untested
		'18': {
			'name': 'Pulse/Frequency Meter',
			'parse': lambda d :	{
				'frequency': reduce(msbLsb, d[0:3]) / 1000,
				'duty_cycle': reduce(msbLsb, d[3:5]) / 100
			}
		},
        # untested
		'19': {
			'name': '2-channel 24-bit Current Monitor',
			'parse': lambda d :	{
				'channel_1': reduce(msbLsb, d[0:3]),
				'channel_2': reduce(msbLsb, d[3:6]),
			}
		},
        # untested
		'20': {
			'name': 'Precision Pressure & Temperature (pA)',
			'parse': lambda d :	{
				'pressure': signInt(reduce(msbLsb, d[0:4]), 32) / 1000,
				'temperature': signInt(reduce(msbLsb, d[4:6]), 16) / 100
			}
		},
        # untested
		'21': {
			'name': 'AMS Pressure & Temperature',
			'parse': lambda d :	{
				'pressure': signInt(reduce(msbLsb, d[0:2]), 16) / 100,
				'temperature': signInt(reduce(msbLsb, d[2:4]), 16) / 100,
			}
		},
        # untested
		'22': {
			'name': 'Voltage Detection Input',
			'parse': lambda d :	{
				'input': d[0]
			}
		},
        # untested
		'23': {
			'name': '2-Channel Thermocouple',
			'parse': lambda d :	{
				'channel_1': signInt(reduce(msbLsb, d[0:4]), 32) / 100,
				'channel_2': signInt(reduce(msbLsb, d[4:8]), 32) / 100
			}
		},
        # untested
		'24': {
			'name': 'Activity Detection',
			'parse': lambda d :	{
				'acc_x': signInt(reduce(msbLsb, d[0:2]), 16),
				'acc_y': signInt(reduce(msbLsb, d[2:4]), 16),
				'acc_z': signInt(reduce(msbLsb, d[4:6]), 16),
				'temp_change': signInt(reduce(msbLsb, d[6:8]), 16)
			}
		},
        # untested
		'25': {
			'name': 'Asset Monitor',
			'parse': lambda d :	{
				'acc_x': signInt(reduce(msbLsb, d[0:2]), 16),
				'acc_y': signInt(reduce(msbLsb, d[2:4]), 16),
				'acc_z': signInt(reduce(msbLsb, d[4:6]), 16),
				'temp_change': signInt(reduce(msbLsb, d[6:8]), 16)
			}
		},
        # untested
		'26': {
			'name': 'Pressure & Temperature Sensor (PSI)',
			'parse': lambda d :	{
				'pressure': signInt(reduce(msbLsb, d[0:4]), 32) / 100,
				'temperature': signInt(reduce(msbLsb, d[4:6]), 16) / 100
			}
		},
        # untested
		'27': {
			'name': 'Environmental',
			'parse': lambda d :	{
				'temperature': signInt(reduce(msbLsb, d[0:2]), 16) / 100,
				'pressure': reduce(msbLsb, d[2:6]) / 100,
				'humidity': reduce(msbLsb, d[6:10]) / 1000,
				'gas_resistance': reduce(msbLsb, d[10:14]),
				'iaq': reduce(msbLsb, d[14:16])
			}
		},
        # untested
		'28': {
			'name': '24-Bit 3-Channel Current Monitor',
			'parse': lambda d :	{
				'channel_1': reduce(msbLsb, d[0:3]),
				'channel_2': reduce(msbLsb, d[4:7]),
				'channel_3': reduce(msbLsb, d[8:11])
			}
		},
        # TODO - test out the double lambda, this seems super un-pythonic so
        # consider re-writing in the future.
        # could lead to poor compatibility
        # untested - extremely untested
		'29': {
			'name': 'Linear Displacement Sensor',
			'parse': lambda d : lambda adc=reduce(msbLsb, d[0:2]) : {
				'adc': adc,
				'position': (adc/1023*100)
			}
		},
        # TODO - test out the double lambda, this seems super un-pythonic so
        # consider re-writing in the future.
        # could lead to poor compatibility
        # untested - extremely untested
		'30': {
			'name': 'Structural Monitoring Sensor',
			'parse': lambda d : lambda adc=reduce(msbLsb, d[0:2]) : {
				'adc': adc,
				'position': (adc/1023*100)
			}
		},
        # untested
		'35': {
			'name': 'One Channel Counter',
			'parse': lambda d :	{
					'counts': reduce(msbLsb, d[0:2])
			}
		},
        # check
        '36': {
            'name': "Two Channel Counter",
            'parse': lambda d :	{
                'counts_1': msbLsb(d[0], d[1]),
                'counts_2': msbLsb(d[2], d[3])
            }
        },
        # untested
        # TODO test this priority
		'37': {
			'name': '7 Channel Push Notification',
            'parse': lambda d :	{
					'input_1': 1 if (d[0] & 1) else 0,
					'input_2': 1 if (d[0] & 2) else 0,
					'input_3': 1 if (d[0] & 4) else 0,
					'input_4': 1 if (d[0] & 8) else 0,
					'input_5': 1 if (d[0] & 16) else 0,
					'input_6': 1 if (d[0] & 32) else 0,
					'input_7': 1 if (d[0] & 64) else 0,
					'adc_1': msbLsb(d[1], d[2]),
					'adc_2': msbLsb(d[3], d[4])
			}
		},
        # untested
		'39': {
			'name': 'RTD Temperature Sensor',
            'parse': lambda d :	{
				'temperature': signInt(reduce(msbLsb, d[0:4]), 32) / 100,
			}
		},
        # TODO rework
        '40': {
            'name': "Vibration",
            'parse': lambda d : {
                'rms_x': signInt(reduce(msbLsb, d[0:3]), 24)/100,
                'rms_y': signInt(reduce(msbLsb, d[3:6]), 24)/100,
                'rms_z': signInt(reduce(msbLsb, d[6:9]), 24)/100,
                'max_x': signInt(reduce(msbLsb, d[9:12]), 24)/100,
                'max_y': signInt(reduce(msbLsb, d[12:15]), 24)/100,
                'max_z': signInt(reduce(msbLsb, d[15:18]), 24)/100,
                'min_x': signInt(reduce(msbLsb, d[18:21]), 24)/100,
                'min_y': signInt(reduce(msbLsb, d[21:24]), 24)/100,
                'min_z': signInt(reduce(msbLsb, d[24:27]), 24)/100,
                'temperature': msbLsb(d[27], d[28])
            }
        },
        # untested
        '41': {
            'name': "RPM",
            'parse': lambda d :	{
				'proximity': msbLsb(d[0], d[1]),
				'rpm': msbLsb(d[2], d[3]) * .25
            }
        },
        # untested
        # source file may have issues. Check
		'50': {
			'name': 'Predictive Maintenance Sensor',
            'parse': lambda d :	{
				'rms_x': signInt(reduce(msbLsb, d[0:3]), 24)/100,
				'rms_y': signInt(reduce(msbLsb, d[3:6]), 24)/100,
				'rms_z': signInt(reduce(msbLsb, d[6:9]), 24)/100,
				'max_x': signInt(reduce(msbLsb, d[9:12]), 24)/100,
				'max_y': signInt(reduce(msbLsb, d[12:15]), 24)/100,
				'max_z': signInt(reduce(msbLsb, d[15:18]), 24)/100,
				'min_x': signInt(reduce(msbLsb, d[18:21]), 24)/100,
				'min_y': signInt(reduce(msbLsb, d[21:24]), 24)/100,
				'min_z': signInt(reduce(msbLsb, d[24:27]), 24)/100,
				'vibration_temperature': signInt(msbLsb(d[27], d[28]), 16),
				'thermocouple_temperature': signInt(reduce(msbLsb, d[29:33]), 32) / 100,
				'current': signInt(reduce(msbLsb, d[33:36]), 24) / 1000
			}
		},
        '80': {
			'name': 'Predictive Maintenance Sensor',
            'parse': lambda d :	'This is a more complex sensor and so is parsed using the defined function "type80"'
		},
        # unsupported
		# '10000':{
        #
		# },
        # untested - departure from source
        # source file may have issues. Check
        # Device no long in use. Support pulled.
		# '10006':{
		# 	'name': "4-Channel 4-20 mA Input",
        #     'parse': lambda d :	{
        #         'channel_1': reduce(msbLsb, d[0:2]),
        #         'channel_2': reduce(msbLsb, d[2:4]),
        #         'channel_3': reduce(msbLsb, d[4:6]),
        #         'channel_4': reduce(msbLsb, d[6:8])
		# 	}
		# },
        # untested  - departure from source
        # source file may have issues. Check
        # Device no long in use. Support pulled.
		# '10007':{
		# 	'name': "4-Channel Current Monitor",
        #     'parse': lambda d :	{
        #         'channel_1': reduce(msbLsb, d[0:3]),
        #         'channel_2': reduce(msbLsb, d[3:6]),
        #         'channel_3': reduce(msbLsb, d[6:9]),
        #         'channel_4': reduce(msbLsb, d[9:12])
		# 	}
		# },
        # unsupported
		# "10012':{

		# }
	}
    return types
def type80(payload, parsed, mac):
    if(payload[7] >> 1 != 0):
        sensor_data = {'error': 'Error found, Sensor Probe may be unattached'}
        return sensor_data
    odr_translate_dict = {
        6: '50Hz',
        7: '100Hz',
        8: '200Hz',
        9: '400Hz',
        10: '800Hz',
        11: '1600Hz',
        12: '3200Hz',
        13: '6400Hz',
        14: '12800Hz',
    }
    odr = odr_translate_dict[payload[9]]
    sensor_data = {
        'mode': payload[8],

        'odr': odr,

        'temperature': signInt(reduce(msbLsb, payload[10:12]), 16) / 100,

        'x_rms_ACC_G': reduce(msbLsb, payload[12:14])/1000,
        'x_max_ACC_G': reduce(msbLsb, payload[14:16])/1000,
        'x_velocity_mm_sec': reduce(msbLsb, payload[16:18]) / 100,
        'x_displacement_mm': reduce(msbLsb, payload[18:20]) / 100,
        'x_peak_one_Hz': reduce(msbLsb, payload[20:22]),
        'x_peak_two_Hz': reduce(msbLsb, payload[22:24]),
        'x_peak_three_Hz': reduce(msbLsb, payload[24:26]),

        'y_rms_ACC_G': reduce(msbLsb, payload[26:28])/1000,
        'y_max_ACC_G': reduce(msbLsb, payload[28:30])/1000,
        'y_velocity_mm_sec': reduce(msbLsb, payload[30:32]) / 100,
        'y_displacement_mm': reduce(msbLsb, payload[32:34]) / 100,
        'y_peak_one_Hz': reduce(msbLsb, payload[34:36]),
        'y_peak_two_Hz': reduce(msbLsb, payload[36:38]),
        'y_peak_three_Hz': reduce(msbLsb, payload[38:40]),

        'z_rms_ACC_G': reduce(msbLsb, payload[40:42])/1000,
        'z_max_ACC_G': reduce(msbLsb, payload[42:44])/1000,
        'z_velocity_mm_sec': reduce(msbLsb, payload[44:46]) / 100,
        'z_displacement_mm': reduce(msbLsb, payload[46:48]) / 100,
        'z_peak_one_Hz': reduce(msbLsb, payload[48:50]),
        'z_peak_two_Hz': reduce(msbLsb, payload[50:52]),
        'z_peak_three_Hz': reduce(msbLsb, payload[52:54]),
    }


    return sensor_data

def msbLsb(m,l):
    return (m<<8)+l

def signInt(i, b):
    i = int(i)
    b = int(b)
    if(i < 1<<(b-1)):
        return i
    return (i - (1<<b) + 1)
