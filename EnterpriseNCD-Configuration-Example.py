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
        # for a full list and breakdown of the packets to send please view the guide at https://ncd.io/ncd-io-wireless-sensor-raw-commands/
        # you will only need to send the Payload of the commands listed there as the library will handle the Digi packet API wrapping
       
        # read sleep duration (using decimal values)
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray([247, 21, 00, 00, 00]))
        
        # set network id (using hex values). 7777 will be the new network ID of the sensor when it reboots out of config mode.
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f7050000007777'))
        
        # set node-id and sleep duration (using hex) (sleep duration determines transmission interval)
        # a7 will be the node id in hex. a7 = 167 in decimal
        # 01a2 will be the sleep duration in seconds 01 = 256 seconds (MSB) a2 = 162 (LSB). Sleep duration in seconds = MSB*256+LSB
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f702000000a70001a2'))
        
        # WARNING using the below command is recommended only for adanced users it is commented out for your protection
        # if you alter this make sure to change your modem's KY parameter to match the passed key.
        # set encryption key (128-bit). The key below that is being set starts at a7 and goes to 29.
        # WARNING configuration mode will not override this setting and the modem key will need to match what is passed in order to reconfigure
        # a factory reset of the sensor is the only way to recover a lost key.
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f20300000000a701a2a915164785f7160ad7a55a1f29'))
        
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

# set the modem's encryption key to the default value for configuration mode.
ncdModem.device.set_parameter("KY", bytearray.fromhex(("55aa55aa55aa55aa55aa55aa55aa55aa")))

# set the modem's encryption key to the value set if the command is uncommented in the above callback
# ncdModem.device.set_parameter("KY", bytearray.fromhex(("a701a2a915164785f7160ad7a55a1f29")))

