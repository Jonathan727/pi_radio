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
import busio
from digitalio import DigitalInOut, Direction, Pull
import board
# Import the SSD1306 module.
import adafruit_ssd1306
# Import Adafruit TinyLoRa
from adafruit_tinylora.adafruit_tinylora import TTN, TinyLoRa


# handle termination signal https://stackoverflow.com/a/24574672/2350083
def sigterm_handler(_signo, _stack_frame):
    # Raises SystemExit(0):
    sys.exit(0)


signal.signal(signal.SIGTERM, sigterm_handler)

# Program Configuration
# TODO: set this via program arguments
_LAUNCH_PERIODIC_MODE_AUTOMATICALLY = False

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
devaddr = bytearray([0x00, 0x00, 0x00, 0x00])
# TTN Network Key, 16 Bytes, MSB
nwkey = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                   0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
# TTN Application Key, 16 Bytes, MSB
app = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
# Initialize ThingsNetwork configuration
ttn_config = TTN(devaddr, nwkey, app, country='US')
# Initialize lora object
lora = TinyLoRa(spi, cs, irq, rst, ttn_config)
# 2b array to store sensor data
data_pkt = bytearray(2)

DATA_PKT_DELAY_SLOW = 5.0
DATA_PKT_DELAY_MEDIUM = 1.0
DATA_PKT_DELAY_FAST = 0.25
# time to delay periodic packet sends (in seconds)
data_pkt_delay = DATA_PKT_DELAY_SLOW

# Spread Factor and Bandwidth
# lora.set_datarate("SF7BW125")
# lora.set_datarate("SF7BW250")
# lora.set_datarate("SF8BW125")
# lora.set_datarate("SF9BW125")
lora.set_datarate("SF10BW125")
# lora.set_datarate("SF11BW125")
# lora.set_datarate("SF12BW125")


def send_pi_data_periodic():
    # hold A and C to cancel periodic mode
    while btnA.value or btnC.value:
        # Set Speed
        global data_pkt_delay
        if not btnA.value:
            data_pkt_delay = DATA_PKT_DELAY_FAST
            display_periodic_delay()
        if not btnB.value:
            data_pkt_delay = DATA_PKT_DELAY_MEDIUM
            display_periodic_delay()
        if not btnC.value:
            data_pkt_delay = DATA_PKT_DELAY_SLOW
            display_periodic_delay()

        print("Sending periodic data...")
        send_pi_data(CPU)
        print('CPU:', CPU)
        time.sleep(data_pkt_delay)

    display.fill(0)
    display.text('* Stopping Periodic Mode *', 15, 0, 1)
    display.show()
    time.sleep(0.5)


def display_periodic_delay():
    display.fill(0)
    display.text('Periodic Delay: ' + str(data_pkt_delay), 2, 0, 1)
    display.show()
    time.sleep(0.5)


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
    display.text('Sent Data!', 15, 15, 1)
    print('Data sent!')
    display.show()
    time.sleep(0.5)


isFirstRun = True

try:
    while True:
        packet = None
        # draw a box to clear the image
        display.fill(0)
        display.text('RasPi LoRaWAN', 35, 0, 1)

        # read the raspberry pi cpu load
        cmd = "top -bn1 | grep load | awk '{printf \"%.1f\", $(NF-2)}'"
        CPU = subprocess.check_output(cmd, shell=True)
        CPU = float(CPU)

        if not btnA.value:
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
            time.sleep(0.1)
        if not btnC.value or (isFirstRun and _LAUNCH_PERIODIC_MODE_AUTOMATICALLY):
            display.fill(0)
            display.text('* Periodic Mode *', 15, 0, 1)
            display.show()
            time.sleep(0.5)
            send_pi_data_periodic()

        display.show()
        time.sleep(.1)

        if isFirstRun:
            isFirstRun = False

finally:
    print("Goodbye")
    display.fill(0)
    display.text('Goodbye!', 15, 0, 1)
    display.show()
