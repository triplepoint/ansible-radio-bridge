#!/usr/bin/env python3
"""
Watch a serial port for messages, and translate them
into published MQTT events.

In order to be reliable, this script should be modified to
include a queue, so that delays in publishing messages don't
result in missed reads on the serial port.
https://docs.python.org/3/library/asyncio-queue.html
But that's a battle for another day.
"""

import json
import os
from datetime import datetime, timezone
from itertools import islice
from typing import Option

import click
import paho.mqtt.publish as publish
import serial


def parse_message(line: str) -> dict:
    """
    Given a string that looks like json with
    a 'msg' element in it, remove the msg element
    and replace it with a set of keys and values
    derived from expanding the msg field on spaces.

    For example, a line string like:
      {"one": "fish","two": "fish","msg": "red fish poop fish"}
    would produce a return dict like:
      {'one': 'fish', 'two': 'fish', 'red': 'fish', 'poop': 'fish'}
    """
    data = json.loads(line)
    message = data['msg']
    del data['msg']

    elements = message.split()
    while elements:
        key = elements.pop(0)
        if elements:
            value = elements.pop(0)
        else:
            value = ""
        data[key] = value

    return data


def parse_and_publish(line: str, mqtt_host: str, mqtt_port: int, mqtt_auth_info: Option[dict, None], mqtt_tls_info: Option[dict, None]):
    # Parse the serial message into a data structure suitable
    # for publishing
    try:
        data = parse_message(line)
    except json.JSONDecodeError:
        print("Error reading message as JSON, skipping: {}".format(line), flush=True)
        continue
    data['_timestamp'] = datetime.now(timezone.utc).timestamp()
    json_data = json.dumps(data)

    print(json_data, flush=True)

    # Publish the message to the MQTT broker
    mqtt_topic = "home/radio/client{}".format(data['_sender_id'])
    publish.single(mqtt_topic, json_data, hostname=mqtt_host,
        port=mqtt_port, auth=mqtt_auth_info, tls=mqtt_tls_info,
        keepalive=30)

    print("Publish complete.", flush=True)


@click.command()
@click.option('--device', envvar='BRIDGE_SERIAL_DEVICE', type=click.Path(exists=True), default="/dev/tty99")
@click.option('--mqtt-host', envvar='BRIDGE_MQTT_HOST', type=click.STRING)
@click.option('--mqtt-port', envvar='BRIDGE_MQTT_PORT', type=click.INT, default=8883)
@click.option('--mqtt-user', envvar='BRIDGE_MQTT_USER', type=click.STRING, default=None)
@click.option('--mqtt-password', envvar='BRIDGE_MQTT_PASSWORD', type=click.STRING, default=None)
@click.option('--mqtt-ca-certs', envvar='BRIDGE_MQTT_CA_CERTS', type=click.Path(exists=True), default=None)
def main(device: str, mqtt_host: str, mqtt_port: int, mqtt_user: str, mqtt_password: str, mqtt_ca_certs: str):

    # Organize the MQTT broker authentication info the way the MQTT library wants it
    mqtt_auth_info = {}
    if mqtt_user:
        mqtt_auth_info['username'] = mqtt_user
    if mqtt_password:
        mqtt_auth_info['password'] = mqtt_password
    if not mqtt_auth_info:
        mqtt_auth_info = None

    # Organize the MQTT broker TLS configuration the way the MQTT library wants it
    mqtt_tls_info = {}
    if mqtt_ca_certs:
        mqtt_tls_info['ca_certs'] = mqtt_ca_certs
    if not mqtt_tls_info:
        mqtt_tls_info = None

    print("Initializing serial port {}".format(device), flush=True)

    ser = serial.Serial(
        port=device,
        baudrate=115200,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS
    )

    print("Listening for messages...", flush=True)

    while(1):
        # Block on readline()'ing the specified serial device
        line = ser.readline()
        print(line, flush=True)

        # If the read line starts with a "*", we'll assume that's
        # some sort of debug logging content and not a message.
        if line[0] == "*":
            continue

        parse_and_publish(line, mqtt_host, mqtt_port, mqtt_auth_info, mqtt_tls_info)

    print("Terminating execution.", flush=True)

    ser.close()


if __name__ == "__main__":
    main()
