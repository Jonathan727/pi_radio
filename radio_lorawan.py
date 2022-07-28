# SPDX-FileCopyrightText: 2018 Brent Rubell for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Example for using the RFM9x Radio with Raspberry Pi and LoRaWAN

Learn Guide: https://learn.adafruit.com/lora-and-lorawan-for-raspberry-pi
Author: Brent Rubell for Adafruit Industries
"""
import threading
import time
import signal
import subprocess
import sys
from micropython import const
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import Adafruit TinyLoRa
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa

# RFM Module Settings
_MODE_SLEEP = const(0x00)
_MODE_LORA = const(0x80)
_MODE_STDBY = const(0x01)
_MODE_TX = const(0x83)
_TRANSMIT_DIRECTION_UP = const(0x00)
# RFM Registers
_REG_PA_CONFIG = const(0x09)
_REG_PREAMBLE_MSB = const(0x20)
_REG_PREAMBLE_LSB = const(0x21)
_REG_FRF_MSB = const(0x06)
_REG_FRF_MID = const(0x07)
_REG_FRF_LSB = const(0x08)
_REG_FEI_LSB = const(0x1E)
_REG_FEI_MSB = const(0x1D)
_REG_MODEM_CONFIG = const(0x26)
_REG_PAYLOAD_LENGTH = const(0x22)
_REG_FIFO_POINTER = const(0x0D)
_REG_FIFO_BASE_ADDR = const(0x80)
_REG_OPERATING_MODE = const(0x01)
_REG_VERSION = const(0x42)
_REG_PREAMBLE_DETECT = const(0x1F)
_REG_TIMER1_COEF = const(0x39)
_REG_NODE_ADDR = const(0x33)
_REG_IMAGE_CAL = const(0x3B)
_REG_RSSI_CONFIG = const(0x0E)
_REG_RSSI_COLLISION = const(0x0F)
_REG_DIO_MAPPING_1 = const(0x40)

_REG_Temp = const(0x3C)

# Button A
btnA = DigitalInOut(board.D5)
btnA.direction = Direction.INPUT
btnA.pull = Pull.UP

# Button B
btnB = DigitalInOut(board.D6)
btnB.direction = Direction.INPUT
btnB.pull = Pull.UP

# Button C
btnC = DigitalInOut(board.D12)
btnC.direction = Direction.INPUT
btnC.pull = Pull.UP

# Create the I2C interface.
i2c = busio.I2C(board.SCL, board.SDA)

# 128x32 OLED Display
reset_pin = DigitalInOut(board.D4)
display = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c, reset=reset_pin)
# Clear the display.
display.fill(0)
display.show()
width = display.width
height = display.height

# TinyLoRa Configuration
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = DigitalInOut(board.CE1)
irq = DigitalInOut(board.D22)
rst = DigitalInOut(board.D25)

# TTN Device Address, 4 Bytes, MSB
devaddr = bytearray([
    0xA0,
    0xFF,
    0xFF,
    0xFF
])
# TTN Network Key, 16 Bytes, MSB
# nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
#                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
nwkey = bytearray([
    0x70,
    0xB3,
    0xD5,
    0x7E,
    0xD0,
    0x05,
    0x35,
    0xB8,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x01])
# TTN Application Key, 16 Bytess, MSB
app = bytearray([
    0x31,
    0x37,
    0x43,
    0x46,
    0xA3,
    0xF4,
    0x7D,
    0x57,
    0xE3,
    0x17,
    0xA4,
    0x7C,
    0x32,
    0x68,
    0x95,
    0x5A
])
# Initialize ThingsNetwork configuration
ttn_config = TTN(devaddr, nwkey, app, country='US')
# Initialize lora object
lora = TinyLoRa(spi, cs, irq, rst, ttn_config)
# lora.set_datarate("SF12BW125")
lora.set_datarate("SF10BW125")
# 2b array to store sensor data
data_pkt = bytearray(2)
# time to delay periodic packet sends (in seconds)
data_pkt_delay = 1.0


# handle termination signal https://stackoverflow.com/a/24574672/2350083
def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)

global periodicTimer
periodicTimer = None


def send_pi_data_periodic():
    global periodicTimer
    if not btnA.value:
        # cancel periodic mode
        if periodicTimer is not None:
            print('Canceling Periodic Timer')
            periodicTimer.cancel()
            periodicTimer = None
        return

    if periodicTimer is not None:
        periodicTimer.cancel()

    periodicTimer = threading.Timer(data_pkt_delay, send_pi_data_periodic).start()
    print("Sending periodic data...")
    send_pi_data(CPU)
    print('CPU:', CPU)


def send_pi_data(data, count=1):
    # Encode float as int
    data = int(data * 100)
    # Encode payload as bytes
    data_pkt[0] = (data >> 8) & 0xff
    data_pkt[1] = data & 0xff
    # Send data packet
    for i in range(count):
        bgColor = (i + 1) % 2
        fgColor = i % 2
        display.fill(bgColor)
        display.text('Sending Packet...' + str(i + 1), 10, 5, fgColor)
        display.text('Frame:' + str(lora.frame_counter), 15, 15, fgColor)
        # display.text('Sending Packet...', 15, 15, 1)
        display.show()
        print('Sending Packet...' + str(i + 1))
        lora.send_data(data_pkt, len(data_pkt), lora.frame_counter)
        lora.frame_counter += 1
    display.fill(0)
    display.text('Sent Data to TTN!', 15, 15, 1)
    print('Data sent!')
    display.show()
    time.sleep(0.5)


try:
    while True:
        packet = None

        if periodicTimer is not None:
            # in periodic mode
            continue
        else:
            # not in periodic mode
            # draw a box to clear the image
            display.fill(0)
            display.text('RasPi LoRaWAN', 35, 0, 1)

        # # reset chip
        # lora._rst.switch_to_output()
        # lora._rst.value = False
        # time.sleep(0.0001)  # 100 us
        # lora._rst.value = True
        # time.sleep(0.005)  # 5 ms
        # # get temp
        # temperatureReg = lora._read_u8(_REG_Temp)
        # myDataArray = bytearray(1)
        # myDataArray[0] = lora._read_u8(_REG_Temp)
        # nodeAddress = lora._read_u8(0x33)
        # temperature = temperatureReg & 0x7F
        # if (temperatureReg & 0x80) == 0x80:
        #     temperature *= -1
        # display.fill(0)
        # display.text('Temperature', 45, 0, 1)
        # # display.text(myDataArray.hex(), 60, 15, 1)
        # display.text(str(temperature), 60, 15, 1)
        # compensationFactor = 130
        # display.text(str(temperature + compensationFactor), 110, 15, 1)
        # # display.text(str(temperature), 0, 15, 1)
        # display.text(temperatureReg.to_bytes(1, 'big').hex(), 0, 15, 1)

        # read the raspberry pi cpu load
        cmd = "top -bn1 | grep load | awk '{printf \"%.1f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True)
        CPU = float(CPU)

        if not btnA.value and btnC.value:
            # Send Packet
            send_pi_data(CPU)
        if not btnB.value:
            # Display CPU Load
            display.fill(0)
            display.text('CPU Load %', 45, 0, 1)
            display.text(str(CPU), 60, 15, 1)
            display.show()
            time.sleep(0.1)
            send_pi_data(CPU, 5)
            # send_pi_data(CPU)
            # send_pi_data(CPU)
            # send_pi_data(CPU)
            # send_pi_data(CPU)
        if not btnC.value and btnA.value:
            display.fill(0)
            display.text('* Periodic Mode *', 15, 0, 1)
            display.show()
            time.sleep(0.5)
            send_pi_data_periodic()

        display.show()
        time.sleep(.1)
finally:
    print('Stopping')
    # cancel periodic mode
    if periodicTimer is not None:
        print('Canceling Periodic Timer')
        periodicTimer.cancel()
        periodicTimer = None
    print("Goodbye")
    display.fill(0)
    display.text('Goodbye!', 15, 0, 1)
    display.show()
