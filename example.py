#!/usr/bin/env python3
# coding=utf-8
import paho.mqtt.client as mqtt
from jsonpath_ng import jsonpath, parse
import wideq
import json
import time
import argparse
import sys
import re
import os.path
import logging
from typing import List
from pprint import pprint

STATE_FILE = 'wideq_state.json'
LOGGER = logging.getLogger("wideq.washer")
MQTT_HOST = '192.168.1.144'
MQTT_PORT = 1883
washer_value_lookup = {}

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def authenticate(gateway):
    """Interactively authenticate the user via a browser to get an OAuth
    session.
    """

    login_url = gateway.oauth_url()
    print('Log in here:')
    print(login_url)
    print('Then paste the URL where the browser is redirected:')
    callback_url = input()
    return wideq.Auth.from_url(gateway, callback_url)


def ls(client):
    """List the user's devices."""

    for device in client.devices:
        print('{0.id}: {0.name} ({0.type.name} {0.model_id})'.format(device))


def mon(client, device_id):
    """Monitor any device, displaying generic information about its
    status.
    """
	#State
	#Remain_Time_H
	#Remain_Time_M
	#Initial_Time_H
	#Initial_Time_M
	#Course
	#Error
	#Soil
	#SpinSpeed
	#WaterTemp
	#RinseOption
	#DryLevel
	#Reserve_Time_H
	#Reserve_Time_M
	#Option1
	#Option2
	#Option3
	#PreState
	#SmartCourse
	#TCLCount
	#LoadItem
	#CourseType
	#Standby

    mclient = mqtt.Client()
    mclient.on_connect = on_connect
    mclient.on_message = on_message

    mclient.connect(MQTT_HOST, MQTT_PORT, 60)

    device = client.get_device(device_id)
    model = client.model_info(device)

    if device.type == wideq.DeviceType.WASHER:
        print('Attempting to poll washer.')
        washer = wideq.WasherDevice(client, device)
        try:
           washer.monitor_start()
        except wideq.core.NotConnectedError:
           print('Device not available.')
           return

        try:
           while True:
            time.sleep(1)
            state = washer.poll()
            if state:
                json_data=client.dump()
                for key in state.keys(): 
                    jsonpath_expression = parse('$.model_info..Value.'+key+'.option."'+state[key]+'"')
                    match = jsonpath_expression.find(json_data)
                    if(match):
                       if(key == 'SpinSpeed' or key == 'RinseOption' or key == 'Soil' or key == 'WaterTemp'):
                            output_value=re.sub("@WM_[A-Z]+_[A-Z]+_","",match[0].value).replace("_W", "").replace("_", " ").title()
                       else:
                            output_value=re.sub("@WM_[A-Z]+_","",match[0].value).replace("_W", "").replace("_", " ").title()
                       state[key] = output_value
                mclient.publish("stat/washer",str(state))
                break
        except KeyboardInterrupt:
            pass
        finally:
            washer.monitor_stop()
            mclient.disconnect()


class UserError(Exception):
    """A user-visible command-line error.
    """
    def __init__(self, msg):
        self.msg = msg


def _force_device(client, device_id):
    """Look up a device in the client (using `get_device`), but raise
    UserError if the device is not found.
    """
    device = client.get_device(device_id)
    if not device:
        raise UserError('device "{}" not found'.format(device_id))
    return device


EXAMPLE_COMMANDS = {
    'ls': ls,
    'mon': mon,
}


def example_command(client, cmd, args):
    func = EXAMPLE_COMMANDS.get(cmd)
    if not func:
        LOGGER.error("Invalid command: '%s'.\n"
                     "Use one of: %s", cmd, ', '.join(EXAMPLE_COMMANDS))
        return
    func(client, *args)


def example(country: str, language: str, verbose: bool,
            cmd: str, args: List[str]) -> None:
    if verbose:
        wideq.set_log_level(logging.DEBUG)

    # Load the current state for the example.
    try:
        with open(STATE_FILE) as f:
            LOGGER.debug("State file found '%s'", os.path.abspath(STATE_FILE))
            state = json.load(f)
    except IOError:
        state = {}
        LOGGER.debug("No state file found (tried: '%s')",
                     os.path.abspath(STATE_FILE))

    client = wideq.Client.load(state)
    if country:
        client._country = country
    if language:
        client._language = language

    # Log in, if we don't already have an authentication.
    if not client._auth:
        client._auth = authenticate(client.gateway)

    # Loop to retry if session has expired.
    while True:
        try:
            example_command(client, cmd, args)
            break

        except wideq.NotLoggedInError:
            LOGGER.info('Session expired.')
            client.refresh()

        except UserError as exc:
            LOGGER.error(exc.msg)
            sys.exit(1)

    # Save the updated state.
    state = client.dump()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)
        LOGGER.debug("Wrote state file '%s'", os.path.abspath(STATE_FILE))
    
def main() -> None:
    """The main command-line entry point.
    """
    parser = argparse.ArgumentParser(
        description='Interact with the LG SmartThinQ API.'
    )
    parser.add_argument('cmd', metavar='CMD', nargs='?', default='ls',
                        help=f'one of: {", ".join(EXAMPLE_COMMANDS)}')
    parser.add_argument('args', metavar='ARGS', nargs='*',
                        help='subcommand arguments')

    parser.add_argument(
        '--country', '-c',
        help=f'country code for account (default: {wideq.DEFAULT_COUNTRY})',
        default=wideq.DEFAULT_COUNTRY
    )
    parser.add_argument(
        '--language', '-l',
        help=f'language code for the API (default: {wideq.DEFAULT_LANGUAGE})',
        default=wideq.DEFAULT_LANGUAGE
    )
    parser.add_argument(
        '--verbose', '-v',
        help='verbose mode to help debugging',
        action='store_true', default=False
    )

    args = parser.parse_args()
    country_regex = re.compile(r"^[A-Z]{2,3}$")
    if not country_regex.match(args.country):
        LOGGER.error("Country must be two or three letters"
                     " all upper case (e.g. US, NO, KR) got: '%s'",
                     args.country)
        exit(1)
    language_regex = re.compile(r"^[a-z]{2,3}-[A-Z]{2,3}$")
    if not language_regex.match(args.language):
        LOGGER.error("Language must be a combination of language"
                     " and country (e.g. en-US, no-NO, kr-KR)"
                     " got: '%s'",
                     args.language)
        exit(1)
    example(args.country, args.language, args.verbose, args.cmd, args.args)


if __name__ == '__main__':
    main()
