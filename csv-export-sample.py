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

    if sensor_data['sensor_type_id'] is 40:
        csv_dict = restructure_data(sensor_data.get('sensor_data'))
        print('data acquired')
        csv_file = open('~/vibration_data.csv', 'a+')
        csv_file.write(csv_dict.get('rms_x_csv')+"\r")
        csv_file.write(csv_dict.get('rms_y_csv')+"\r")
        csv_file.write(csv_dict.get('rms_z_csv')+"\r\r")
        csv_file.close()

def restructure_data(data):
    r_data = {'rms_x_csv': '\"RMS_X\",', 'rms_y_csv': '\"RMS_Y\",', 'rms_z_csv': '\"RMS_Z\",'}
    for sample in data:
        r_data['rms_x_csv'] += '\"'+str(data.get(sample)['rms_x']) +'\",'
        r_data['rms_y_csv'] += '\"'+str(data.get(sample)['rms_y']) +'\",'
        r_data['rms_z_csv'] += '\"'+str(data.get(sample)['rms_z']) +'\",'
    return r_data


#instantiate the NCDEnterprise Object and pass in the Serial Port, Baud Rate,
# and Function/Method object
ncdModem = NCDEnterprise(SERIAL_PORT, BAUD_RATE, my_custom_callback)
# print(ncdModem.device.serial_port.rts)
