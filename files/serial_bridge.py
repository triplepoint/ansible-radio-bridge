#!/usr/bin/env python3
"""
Watch a serial port for messages, and translate them
into published MQTT events.
"""

import json
import os
from datetime import datetime, timezone
from itertools import islice

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


def define_auth_info(mqtt_user, mqtt_password):
    mqtt_auth_info = {}

    if mqtt_user:
        mqtt_auth_info['username'] = mqtt_user
    if mqtt_password:
        mqtt_auth_info['password'] = mqtt_password

    if not mqtt_auth_info:
        mqtt_auth_info = None

    return mqtt_auth_info


def define_tls_info(mqtt_ca_certs):
    mqtt_tls_info = {}

    if mqtt_ca_certs:
        mqtt_tls_info['ca_certs'] = mqtt_ca_certs

    if not mqtt_tls_info:
        mqtt_tls_info = None

    return mqtt_tls_info


@click.command()
@click.option('--device', envvar='BRIDGE_SERIAL_DEVICE', type=click.Path(), default="/dev/tty99")
@click.option('--mqtt-host', envvar='BRIDGE_MQTT_HOST')
@click.option('--mqtt-port', envvar='BRIDGE_MQTT_PORT', default=8883)
@click.option('--mqtt-user', envvar='BRIDGE_MQTT_USER', default=None)
@click.option('--mqtt-password', envvar='BRIDGE_MQTT_PASSWORD', default=None)
@click.option('--mqtt-ca-certs', envvar='BRIDGE_MQTT_CA_CERTS', type=click.Path(), default=None)
def main(device, mqtt_host, mqtt_port, mqtt_user, mqtt_password, mqtt_ca_certs):

    mqtt_auth_info = define_auth_info(mqtt_user, mqtt_password)

    mqtt_tls_info = define_tls_info(mqtt_ca_certs)

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
        # some sort of logging content and not a message.
        if line[0] == "*":
            continue

        # Parse the serial message into a data structure suitable
        # for publishing
        try:
            data = parse_message(line)
        except json.JSONDecodeError:
            print("Error reading message as JSON, skipping")
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

    ser.close()


if __name__ == "__main__":
    main()
