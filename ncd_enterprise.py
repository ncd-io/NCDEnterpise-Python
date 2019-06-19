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
        # self.mems_buffer = {'time': False, 'data': {}}
        self.mems_buffer = {}

    def send_data_to_address(self, address, data):
        # print('send_data_to_address')
        # print(address)
        # print(type(data))
        remote_device = RemoteDigiMeshDevice(self.device, XBee64BitAddress.from_hex_string(address))
        self.device.send_data(remote_device, data)

    # def parse(self, xbee_packet):
    #     if not isinstance(xbee_packet, ATCommResponsePacket):
    #         data = xbee_packet.rf_data
    #         packet_type = self.payload_type[str(data[0])]
    #         if(callable(getattr(self, packet_type))):
    #             getattr(self, packet_type)(data[1:], xbee_packet.x64bit_source_addr)
    #     else:
    #         print(xbee_packet)

    def parse(self, xbee_packet):
        if not isinstance(xbee_packet, ATCommResponsePacket):
            data = xbee_packet.rf_data
            packet_type = self.payload_type[str(data[0])]


            # print(data[2])
            # if the length is exactly 180, assume it is a mems data packet
            if(len(data) == 180):
                self.buffer_mems(data[1:], xbee_packet.x64bit_source_addr)
                return

            # print(xbee_message.data[6])
            # print(xbee_message.data[7])
            type = self.payload_type[str(data[0])]
            # print('parse')
            if(callable(getattr(self, packet_type))):
                getattr(self, packet_type)(data[1:], xbee_packet.x64bit_source_addr)
        else:
            print(xbee_packet)



        # self.sensor_data(xbee_message.data[1:])

    def buffer_mems(self, payload, source_address):
        source_address = str(source_address)
        if not self.mems_buffer.get(str_source_address, False):
            self.mems_buffer[str_source_address] = {}

        if payload[1] not in self.mems_buffer.get(str_source_address):
            self.mems_buffer[str_source_address][payload[1]] = payload[4:]
        else:
            print('error reported')

        # print(self.mems_buffer)
        if(len(self.mems_buffer.get(str_source_address)) == 12):
            self.parse_mems(self.mems_buffer.get(str_source_address), str_source_address)
            self.mems_buffer[str_source_address] = {}

    # def buffer_mems(self, payload, source_address):
    #     if self.mems_buffer['time'] < time.time()-5:
    #         self.mems_buffer = {'time': False, 'data': {}}
    #
    #     if not self.mems_buffer['time']:
    #         self.mems_buffer['time'] = time.time()
    #
    #     if payload[1] not in self.mems_buffer['data']:
    #         self.mems_buffer['data'][payload[1]] = payload[4:]
    #     else:
    #         print('error reported')
    #
    #     # print(self.mems_buffer)
    #     if(len(self.mems_buffer['data']) == 12):
    #         self.parse_mems(self.mems_buffer['data'], source_address)
    #         self.mems_buffer = {'time': False, 'data': {}}

    def parse_mems(self, mems_dict, source_address):
        # print(mems_dict)
        readings = 29
        bytes_in_single = 6
        reading_array = {}
        for index, packet in enumerate(mems_dict):
            packet_data = mems_dict.get(packet)[5:]
            packet_array = {}
            for reading in range(1, readings+1):

                if index is not 12 and reading < 22:
                    reading_array[((index*readings)+reading)] = packet_data[((reading-1)*(bytes_in_single)):(reading-1)*(bytes_in_single)+bytes_in_single]

        for sample in reading_array:
            print('77777')
            # print(type(bytearray(sample)))
            sample_data = reading_array.get(sample)
            reading_array[sample] = {
                'rms_x': signInt(reduce(msbLsb, sample_data[0:2]), 16),
                'rms_y': signInt(reduce(msbLsb, sample_data[2:4]), 16),
                'rms_z': signInt(reduce(msbLsb, sample_data[4:6]), 16)
            }
        print(reading_array)
        parsed = {
            'nodeId': mems_dict[1][0],
            'firmware': "NA",
            'battery': "NA",
            'battery_percent': str(((msbLsb(mems_dict[1][2], mems_dict[1][3]) * 0.00322) - 1.3)/2.03*100) + "%",
            'counter': "NA",
            'sensor_type_id': 40,
            'source_address': str(source_address),
            'sensor_type_string': "Vibration Time Series",
            'sensor_data': reading_array
        }
        self.callback(parsed)
        # return reading_array
        print("!!!!!!!!!!!!!!!!!")


    def sensor_data(self, payload, source_address):
        # print(payload)
        parsed = {
            'nodeId': payload[0],
            'firmware': payload[1],
            'battery': msbLsb(payload[2], payload[3]) * 0.00322,
            'battery_percent': str(((msbLsb(payload[2], payload[3]) * 0.00322) - 1.3)/2.03*100) + "%",
            'counter': payload[4],
            'sensor_type_id': msbLsb(payload[5], payload[6]),
            'source_address': str(source_address),
        }
        parsed['sensor_type_string'] = self.sensor_types[str(parsed['sensor_type_id'])]['name']
        parsed['sensor_data'] = self.sensor_types[str(parsed['sensor_type_id'])]['parse'](payload[8:])

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
        "1": {
            'name': "Temperature/Humidity",
            'parse':  lambda d : {
                'humidity': msbLsb(d[0], d[1])/100,
                'temperature': (msbLsb(d[2], d[3])/100)
            }
        },
        # check
        "2": {
            'name': "2 Channel Push Notification",
            'parse': lambda d :	{
                'input_1': d[0],
                'input_2': d[1]
            }
        },
        # check
        "3": {
            'name': "ADC",
            'parse': lambda d :	{
                'input_1': msbLsb(d[0], d[1]),
                'input_2': msbLsb(d[2], d[3])
            }
        },
        # check
        "4": {
            'name': "Thermocouple",
            'parse': lambda d :	{
                'temperature': reduce(msbLsb, d[0:4])/100
            }
        },
        # check
        "5": {
            'name': "Gyro/Magneto/Temperature",
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
        # check
        "6": {
            'name': "Temperature/Barometeric Pressure",
            'parse': lambda d :	{
                'temperature': msbLsb(d[0], d[1]),
                'absolute_pressure': msbLsb(d[2], d[3])/1000,
                'relative_pressure': signInt(msbLsb(d[4], d[5]), 16)/1000,
                'altitude_change': signInt(msbLsb(d[6], d[7]), 16)/100
            }
        },
        # check
        "8": {
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
		# "9": {
		# 	'name': "Proximity",
		# 	'parse': lambda d :	{
		# 		'proximity': msbLsb(d[0], d[1]),
		# 		'lux': msbLsb(d[2], d[3]) * .25
		# 	}
		# },
        # check
        "10": {
            'name': "Light",
            'parse': lambda d :	{
                'lux': reduce(msbLsb, d[0:3])
            }
        },
        # untested
		# "13": {
		# 	'name': "Current Monitor",
		# 	'parse': lambda d :	{
		# 		'amps': reduce(msbLsb, d[0:3])/1000
		# 	}
		# },
		# "25": {
		# 	'name': "7 Channel Push Notification",
		# 	'parse': lambda d :	{
		# 		'input_1': 1 if(d[0] & 1) else 0,
		# 		'input_2': 1 if(d[0] & 2) else 0,
		# 		'input_3': 1 if(d[0] & 4) else 0,
		# 		'input_4': 1 if(d[0] & 8) else 0,
		# 		'input_5': 1 if(d[0] & 16) else 0,
		# 		'input_6': 1 if(d[0] & 32) else 0,
		# 		'input_7': 1 if(d[0] & 64) else 0,
		# 		'adc_1': msblsb(d[1], d[2]),
		# 		'adc_2': msblsb(d[3], d[4]),
		# 	}
		# },
		# "35": {
		# 	'name': "One Channel Counter",
		# 	'parse': lambda d :	{
		# 		'counts': reduce(msbLsb, d[0:4])
		# 	}
		# },
        # check
        "36": {
            'name': "Two Channel Counter",
            'parse': lambda d :	{
                'counts_1': msbLsb(d[0], d[1]),
                'counts_2': msbLsb(d[2], d[3])
            }
        },
        "40": {
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
        "41": {
            'name': "Unknown",
            'parse': lambda d :	{
                'counts_1': msbLsb(d[0], d[1]),
                'counts_2': msbLsb(d[2], d[3])
            }
        },
        # untested
		# "10006":{
		# 	'name': "4-Channel 4-20 mA Input",
		# 	'parse': (d) => {
		# 		var readings = {};
		# 		for(var i=0;i++;i<4) readings[`channel_${i+1}`] = d.slice((i*2), 1+(i*2)).reduce(msbLsb) / 100;
		# 		return readings;
		# 	}
		# },
		# "10007":{
		# 	'name': "4-Channel Current Monitor",
		# 	'parse': (d) => {
		# 		var readings = {};
		# 		for(var i=0;i++;i<4) readings[`channel_${i+1}`] = d.slice((i*3), 2+(i*3)).reduce(msbLsb) / 1000;
		# 		return readings;
		# 	}
		# },
		# "10012":{
		# 	'name': "2-Relay + 2-Input",
		# 	'parse': lambda d :	{
		# 		'relay_1': d[0],
		# 		'relay_2': d[1],
		# 		'input_1': "On" if(d[2]) else "Off",
		# 		'input_2': "On" if(d[3]) else "Off"
		# 	}
		# }
	}
    return types

def msbLsb(m,l):
    return (m<<8)+l

def signInt(i, b):
    print('+++')
    print(i)
    print(b)
    i = int(i)
    b = int(b)
    print(i)
    print(b)
    if(i < 1<<(b-1)):
        return i
    return (i - (1<<b) + 1)

# def my_custom_callback(sensor_data):
#     print('full return: '+str(sensor_data))
#     for prop in sensor_data:
#         print(prop + ' ' + str(sensor_data[prop]))
#     # print('sensor_data: '+str(sensor_data['sensor_data']))
#     # print('sensor_type_id: '+str(sensor_data['sensor_type_id']))
#     # print('sensor_type_name: '+sensor_data['sensor_type_name'])
#     # print('counter: '+sensor_data['counter'])
#     # print('battery: '+sensor_data['battery'])
#     # print('firmware: '+sensor_data['firmware'])
#     # print('nodeId: '+sensor_data['nodeId'])

# testobj = EnterpriseNCD("/dev/tty.usbserial-A8004V35", 115200, 'ingress')
# testobj.stop()
