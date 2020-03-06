# NCDEnterpise-Python
A Python Library to Interface to our Enterprise Wireless Line

## Installation
This module doesn't currently have an install package. To install it you'll need to install the python-xbee module.
It is recommended to use Python 3 and the Python XBee package version 1.1.1.1. To install this on a linux/mac machine you can use the command 

```python3 -m pip install digi-xbee==1.1.1.1``` 

Newer versions of the digi-xbee libraries are not supported.

Additional information can be found at https://github.com/digidotcom/python-xbee

Once that's installed simply put the ncd_enterprise.py file in your python applications directory and reference it with the import function.

## Use
This library will accept a function as a callback. When the modem receives data it will transmit it to the computer over serial. When this library sees data on the serial line it will break it down and interpret it and send a keyed array to the callback function sent in during instantiation.

## Commands

### stop()
NOT FULLY TESTED - Should stop the library from reading the serial port, close the serial port, and close the extra thread.

### start()
NOT FULLY TESTED - Should open the serial port and the thread to begin reading.
