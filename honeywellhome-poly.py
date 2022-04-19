#!/usr/bin/env python3
from thermostat import Thermostat
from indoor_air_sensor import IndoorAirSensor

import udi_interface
import sys
import os

from api_helper import ApiHelper

LOGGER = udi_interface.LOGGER


class Controller(udi_interface.Node):
    def __init__(self, polyglot, primary, address, name):
        super(Controller, self).__init__(polyglot, primary, address, name)
        self.name = "Honeywell Home Controller"
        self._client_id = ""
        self._client_secret = ""
        self._user_id = ""
        self._api_baseurl = "https://api.honeywell.com"
        self._api = None

        polyglot.subscribe(polyglot.CUSTOMPARAMS, self.parameterHandler)
        polyglot.subscribe(polyglot.START, self.start, address)
        polyglot.subscribe(polyglot.POLL, self.poll)

        polyglot.ready()
        polyglot.addNode(self)

    def parameterHandler(self, params):
        if 'client_id' in params:
            self._client_id = params['client_id']
        else:
            LOGGER.error('check_params: client_id not defined in customParams, please add it.  Using {}'.format(self._client_id))

        if 'client_secret' in params:
            self._client_secret = params['client_secret']
        else:
            LOGGER.error('check_params: client_secret not defined in customParams, please add it.  Using {}'.format(self._client_secret))

        if 'user_id' in params:
            self._user_id = params['user_id']
        else:
            LOGGER.error('check_params: user_id not defined in customParams, please add it.  Using {}'.format(self._user_id))

        self.poly.Notices.clear()
        # Add a notice if they need to change the user/password from the default.
        if self._client_id == "" or self._client_secret == "" or self._user_id == "":
            self.poly.Notices['mynotice'] = 'Please set proper client_id and client_secret in configuration page. See:<br />https://github.com/dbarentine/udi-honeywellhome-poly/blob/master/README.md'
            return False
        else:
            self._api = ApiHelper(self._api_baseurl, self._client_id, self._client_secret, self._user_id)
            self.discover()
            self.setDriver('ST', 1)
            return True

    def start(self):
        LOGGER.info('Started Honeywell Home Nodeserver')
        self.poly.updateProfile()
        self.poly.setCustomParamsDoc()

    def poll(self, polltype):
        if 'longPoll' in polltype:
            self.query()

    def query(self):
        for node in self.poly.nodes():
            if node is not self:
                node.query()

            node.reportDrivers()

    def discover(self, *args, **kwargs):
        try:
            LOGGER.debug("Starting discovery")
            # If this is a re-discover than update=True
            update = len(args) > 0

            locations = self._api.get_locations()
            for location in locations:
                if location.devices is None:
                    LOGGER.warn("There were no devices for location {0}", location.name)
                    continue

                for thermostat in location.devices:
                    self.add_thermostat(location.location_id, location.name, thermostat, update)

            LOGGER.info("Discovery Finished")
        except Exception as ex:
            self.poly.Notices['disc'] = 'Discovery failed please check logs for a more detailed error.'
            LOGGER.exception("Discovery failed with error %s", ex)

    def add_thermostat(self, location_id, location_name, thermostat, update):
        t_name = location_name + ' - ' + thermostat['userDefinedDeviceName']
        t_device_id = thermostat['deviceID']
        t_addr = thermostat['macID'].lower()
        use_celsius = thermostat['units'].lower() != 'fahrenheit'

        LOGGER.debug('Adding thermostat with id {0} and name {1} and addr {2}'.format(t_device_id, t_name, t_addr))
        self.poly.addNode(Thermostat(self.poly, t_addr, t_addr, t_name, self._api, location_id, t_device_id, use_celsius), update)

        if 'groups' not in thermostat:
            return

        for group in thermostat['groups']:
            group_id = group['id']

            sensors = self._api.get_sensors(location_id, t_device_id, group_id)
            for sensor in sensors.rooms:
                if len(sensor.accessories) == 0:
                    continue

                # TODO: Do we ever have to care about multiple accessory blocks?
                sensor_type = sensor.accessories[0].accessory_attribute.type
                sensor_name = sensor.name
                sensor_addr = t_addr + str(group_id) + str(sensor.id)

                if sensor_type == 'IndoorAirSensor' or sensor_type == 'Thermostat':
                    LOGGER.debug('Adding IndoorAirSensor with name {0} and addr {1} for thermostat {2}'.format(sensor_name, sensor_addr, t_addr))
                    self.poly.addNode(IndoorAirSensor(self.poly, t_addr, sensor_addr, sensor_name, self._api, location_id, t_device_id, group_id, sensor.id, use_celsius))

    def delete(self):
        LOGGER.info('Honeywell Home NS Deleted')

    def stop(self):
        LOGGER.debug('Honeywell Home NS stopped.')

    id = 'controller'
    commands = {
        'DISCOVER': discover,
    }

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


if __name__ == "__main__":
    try:
        polyglot = udi_interface.Interface([])
        polyglot.start('2.0.0')
        Controller(polyglot, 'controller', 'controller', 'HoneywellHome')
        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
