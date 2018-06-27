# NCDEnterpise-Python
A Python Library to Interface to our Enterprise Wireless Line

## Installation
This module doesn't currently have an install package. To install it you'll need to install the python-xbee module from https://github.com/digidotcom/python-xbee

Once that's installed simply put the ncd_enterprise.py file in your python applications directory and reference it with the import function.

## Commands

### stop()
NOT FULLY TESTED - Should stop the library from reading the serial port, close the serial port, and close the extra thread.

### start()
NOT FULLY TESTED - Should open the serial port and the thread to begin reading.
