#TODO the NCDEnterprise library requires the digi Xbee library from:
#https://github.com/digidotcom/python-xbee
# someday I may make an install package, but today is not that day.
from ncd_enterprise import NCDEnterprise

#TODO Change this line to your Serial Port
SERIAL_PORT = "/dev/cu.usbserial-AI02QZQZ"
BAUD_RATE = 115200

#this function is the callback that I pass into the NCDEnterprise module during
#instantiation. The module uses the Digi XBee module which runs on another thread.
# This particular example tells the modem to change its network ID to 7bcd (configration network ID)
 # and then waits for any broadcast from a sensor in configuration mode so it can alter settings.
def my_custom_callback(sensor_data):
    print('full return: '+str(sensor_data))
    for prop in sensor_data:
        print(prop + ' ' + str(sensor_data[prop]))
    if(sensor_data['mode'] == 'PGM'):
        print(sensor_data['source_address'])
        print('below is the sleep duration')
        # for a full list and breakdown of the packets to send please view the guide at https://ncd.io/ncd-io-wireless-sensor-raw-commands/
        # read sleep duration (using decimal values)
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray([247, 21, 00, 00, 00]))
        # set network id (using hex values). 7777 will be the new network ID of the sensor when it reboots out of config mode.
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f7050000007777'))
        # set node-id and sleep duration (using hex) (sleep duration determines transmission interval)
        # 07 will be the node id in hex. a7 = 167
        # 01a2 will be the sleep duration in seconds 01 = 256 seconds (MSB) a2 = 162 (LSB). Sleep duration in seconds = MSB*256+LSB
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f702000000a701a2'))
        
#instantiate the NCDEnterprise Object and pass in the Serial Port, Baud Rate,
# and Function/Method object
ncdModem = NCDEnterprise(SERIAL_PORT, BAUD_RATE, my_custom_callback)
# use the digi library objects to change the network id of the ncdModem to the configuration setting 7bcd
# the modem, unlike the sensors, will not overwrite this setting on it's own.
# If you want the modem to return to normal data collection processes it needs to be set to the network ID of the sensors (default: 7fff)

# set the modem's network ID to the configuration network ID
ncdModem.device.set_parameter("ID", bytearray.fromhex(("7bcd")))

# set the modem's network ID to the default network ID
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7fff")))

# set the modem's network ID to 7777 to match the setting stored in this example.
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7777")))
