#!/usr/bin/python
from bootload import bootload
from config import *
import pathlib
import datetime
import os
import sys
import serial
import time
import subprocess
import csv


def main():
    # Make results directory if it doesn't exist
    base_dir = pathlib.Path(__file__).parent
    pathlib.Path(base_dir / 'results').mkdir(exist_ok=True)
    # Use timestamp for results file
    results_path = base_dir / 'results' / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + '.csv')
    results_writer = csv.writer(open(results_path, 'w', newline=''))

    successes = 0
    failures = 0
    retries = 0
    for attempt in range(NUMBER_OF_CYCLES):
        # unplug the usb cables (SRAM is totally turned off)
        subprocess.run([YKUSHCMD_PATH, "-d", "a"], stdin=None,
                       stdout=None, stderr=None, shell=False)
        # wait for the SRAM cells to get their default values
        time.sleep(5)
        # plug the usb cables
        subprocess.run([YKUSHCMD_PATH, "-u", "a"], stdin=None,
                       stdout=None, stderr=None, shell=False)
        # wait for the nRF to bootload
        time.sleep(10)

        # flash the firmware into the SCuM chip through the nRF
        # the nRF will send back a confirmation when done
        try:
            bootload(NRF_PORT, BINARY_IMAGE)
        except:
            retries += 1
            continue

        start_timestamp = time.time()

        # open the serial port with SCuM
        uart_ser = serial.Serial(
            timeout=70,
            port=SERIAL_PORT,
            baudrate=19200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS)

        if uart_ser.is_open != 1:
            uart_ser.open()

        failures += 1

        # read the output of the firmware running on SCuM
        # print('Reading the serial port.')
        while uart_ser.is_open:
            data = uart_ser.readline()
            if data.startswith(LOOK_FOR_STR):
                results_writer.writerow([start_timestamp, time.time(), data.lstrip(LOOK_FOR_STR)])
                successes += 1
                failures -= 1
            # when finishing this round close the serial port with SCuM to allow
            # the nRF to use it later
            elif data.startswith(b'TEST DONE'):
                uart_ser.close()
        print(f'Total attempts: {attempt+1}\tSucceeded: {successes}\tFailed: {failures}\tRetried: {retries}')


if __name__ == '__main__':
    if os.name == 'posix' and os.geteuid() != 0:
        print('Must run as root')
        sys.exit(1)
    if not pathlib.Path(YKUSHCMD_PATH).is_file():
        print('Executable ykushcmd not found, check config.py or file permissions')
        sys.exit(1)
    main()
