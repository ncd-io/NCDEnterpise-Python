#TODO the NCDEnterprise library requires the digi Xbee library from:
#https://github.com/digidotcom/python-xbee
# someday I may make an install package, but today is not that day.
from ncd_enterprise import NCDEnterprise
import time

#TODO Change this line to your Serial Port
SERIAL_PORT = "/dev/cu.usbserial-AC4CF4AA"
BAUD_RATE = 115200

#this function is the callback that I pass into the NCDEnterprise module during
#instantiation. The module uses the Digi XBee module which runs on another thread.
# This particular example tells the modem to change its network ID to 7bcd (configration network ID)
 # and then waits for any broadcast from a sensor in configuration mode so it can alter settings.
def my_custom_callback(sensor_data):
    for prop in sensor_data:
        print(prop + ' ' + str(sensor_data[prop]))

    # ignore any message from a sensor that isn't in Program Mode.
    # The sensor sends a special packet when its in program mode that we if check here
    if(sensor_data['mode'] == 'PGM'):
        time.sleep(.5)
        # # set network id (using hex values). 7f0f will be the new network ID of the sensor when it reboots out of config mode.
        # if you have or want multiple sensor networks, this is the value to change.
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f7050000007777'))
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f7050000007f00'))
        # # set node-id and sleep duration (using hex) (sleep duration determines transmission interval)
        # # a7 will be the node id in hex. a7 = 167 in decimal
        # # 0001a2 will be the sleep duration in seconds 01 = 256 seconds (MSB) a2 = 162 (LSB). Sleep duration in seconds = MSB*256+LSB
        time.sleep(.5)
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f70200000006000105'))
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f702000000a700000a'))
        time.sleep(.5)
        # WARNING using the below command is recommended only for adanced users it is commented out for your protection
        # if you alter this make sure to change your modem's KY parameter to match the passed key.
        # set encryption key (128-bit). The key below that is being set starts at a7 and goes to 29.
        # you should be sending exactly 32 characters or 16 bytes in hex for this value
        # if you receive errors after setting this value, you will need to do a factory reset.
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f20300000000a701a2a915164785f7160ad7a55a1f29'))
        # below is a command to send the default encryption key.
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('f2030000000055aa55aa55aa55aa55aa55aa55aa55aa'))
        # time.sleep(.5)

        # the following command will set the destination address of the sensor's wireless module
        # this command will set the destination address of the wireless module to 0000ffff.
        # this is the reserved broadcast to all devices address.
        ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('F7030000000000ffff'))
        # the following commented out command will set the destination address to a particular module
        # with the lower serial address of 41788fa6
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('F70300000041788fa6'))
        # time.sleep(.5)


        # TODO add support for the following:
        # for a full list and breakdown of the packets to send please view the guide at https://ncd.io/ncd-io-wireless-sensor-raw-commands/
        # read sleep duration (using decimal values)
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray([247, 21, 00, 00, 00]))
        # time.sleep(.5)
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('F7160000000d'))
        # ncdModem.send_data_to_address(sensor_data['source_address'], bytearray.fromhex('F70400000003000000'))



# instantiate the NCDEnterprise Object and pass in the Serial Port, Baud Rate,
# and Function/Method object
ncdModem = NCDEnterprise(SERIAL_PORT, BAUD_RATE, my_custom_callback)
# use the digi library objects to change the network id of the ncdModem to the configuration setting 7bcd
# the modem, unlike the sensors, will not overwrite this setting on it's own.
# If you want the modem to return to normal data collection processes it needs to be set to the network ID of the sensors (default: 7fff)

# set the modem's network ID to the configuration network ID
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7bcd")))
ncdModem.device.set_parameter("ID", bytearray.fromhex(("7f0f")))
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7ff0")))
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7fff")))

# time.sleep(.1)
# set the modem's network ID to the default network ID
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7fff")))

# set the modem's network ID to 7777 to match the setting stored in this example.
# ncdModem.device.set_parameter("ID", bytearray.fromhex(("7777")))

# set the modem's encryption key to the default value for configuration mode.
ncdModem.device.set_parameter("KY", bytearray.fromhex(("55aa55aa55aa55aa55aa55aa55aa55aa")))
# ncdModem.device.set_parameter("KY", bytearray.fromhex(("a701a2a915164785f7160ad7a55a1f29")))
