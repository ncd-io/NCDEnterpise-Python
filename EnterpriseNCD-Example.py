#TODO the NCDEnterprise library requires the digi Xbee library from:
#https://github.com/digidotcom/python-xbee
# someday I may make an install package, but today is not that day.
from ncd_enterprise import NCDEnterprise

#TODO Change this line to your Serial Port

# SERIAL_PORT = "/dev/tty.usbserial-AC4CF4AA"
SERIAL_PORT = "/dev/cu.usbserial-AC4CF4AA"
BAUD_RATE = 115200

#this is function is the callback that I pass into the NCDEnterprise module during
#instantiation. The module uses the Digi XBee module which runs on another thread.
def my_custom_callback(sensor_data):
    print('full return: '+str(sensor_data))
    for prop in sensor_data:
        print(prop + ' ' + str(sensor_data[prop]))

#instantiate the NCDEnterprise Object and pass in the Serial Port, Baud Rate,
# and Function/Method object
ncdModem = NCDEnterprise(SERIAL_PORT, BAUD_RATE, my_custom_callback)
# print(ncdModem.device.serial_port.rts)
