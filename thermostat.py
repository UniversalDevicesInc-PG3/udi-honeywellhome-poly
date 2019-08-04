try:
    import polyinterface

    CLOUD = False
except ImportError:
    import pgc_interface as polyinterface

    CLOUD = True

from copy import deepcopy
from utilities import *

LOGGER = polyinterface.LOGGER

driversMap = {
    'HwhF': [
        {'driver': 'ST', 'value': 0, 'uom': '17'},
        {'driver': 'CLISPH', 'value': 0, 'uom': '17'},
        {'driver': 'CLISPC', 'value': 0, 'uom': '17'},
        {'driver': 'CLIMD', 'value': 0, 'uom': '67'},
        {'driver': 'CLIFS', 'value': 0, 'uom': '68'},
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'},
        {'driver': 'CLIHCS', 'value': 0, 'uom': '66'},
        {'driver': 'CLIFRS', 'value': 0, 'uom': '80'},
        {'driver': 'GV1', 'value': 0, 'uom': '25'},
        {'driver': 'GV2', 'value': 0, 'uom': '25'},
        {'driver': 'GV3', 'value': 0, 'uom': '25'},
        {'driver': 'GV4', 'value': 0, 'uom': '25'},
        {'driver': 'GV5', 'value': int(False), 'uom': '2'},
        {'driver': 'GV6', 'value': int(False), 'uom': '2'},
    ],
    'HwhC': [
        {'driver': 'ST', 'value': 0, 'uom': '4'},
        {'driver': 'CLISPH', 'value': 0, 'uom': '4'},
        {'driver': 'CLISPC', 'value': 0, 'uom': '4'},
        {'driver': 'CLIMD', 'value': 0, 'uom': '67'},
        {'driver': 'CLIFS', 'value': 0, 'uom': '68'},
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'},
        {'driver': 'CLIHCS', 'value': 0, 'uom': '66'},
        {'driver': 'CLIFRS', 'value': 0, 'uom': '80'},
        {'driver': 'GV1', 'value': 0, 'uom': '25'},
        {'driver': 'GV2', 'value': 0, 'uom': '25'},
        {'driver': 'GV3', 'value': 0, 'uom': '25'},
        {'driver': 'GV4', 'value': 0, 'uom': '25'},
        {'driver': 'GV5', 'value': int(False), 'uom': '2'},
        {'driver': 'GV6', 'value': int(False), 'uom': '2'},
    ]
}

modeMap = {
    'Off': 0,
    'Heat': 1,
    'Cool': 2,
    'Auto': 3
}

fanMap = {
    'Auto': 0,
    'On': 1,
    'Circulate': 6,
}

runningStateMap = {
    'EquipmentOff': 0,
    'Heat': 1,
    'Cool': 2,
}

priorityTypeMap = {
    'PickARoom': 0,
    'FollowMe': 1,
    'WholeHouse': 2
}

scheduleStatusMap = {
    'Pause': 0,
    'Resume': 1
}

scheduleModeMap = {
    'Wake': 0,
    'Away': 1,
    'Home': 2,
    'Sleep': 3,
    'Custom': 4
}

setHoldStatusMap = {
    0: 'NoHold',
    1: 'TemporaryHold',
    2: 'PermanentHold',
}

holdStatusMap = {
    'NoHold': 0,
    'HoldUntil': 1,
    'PermanentHold': 2
}


class Thermostat(polyinterface.Node):

    def __init__(self, controller, primary, address, name, api, location_id, thermostat_id, is_celsius):
        self.controller = controller
        self._api = api
        self._location_id = location_id
        self._thermostat_id = thermostat_id
        self._use_celsius = is_celsius
        self.type = 'thermostat'
        self.id = 'HwhC' if self._use_celsius else 'HwhF'
        self.drivers = self._convertDrivers(driversMap[self.id]) if CLOUD else deepcopy(driversMap[self.id])

        super(Thermostat, self).__init__(controller, primary, address, name)

    def start(self):
        self.query()

    def query(self):
        try:
            LOGGER.debug("Query thermostat {}".format(self.address))
            thermostat = self._api.get_thermostat(self._location_id, self._thermostat_id)

            updates = {
                'ST': to_driver_value(thermostat.indoor_temperature, False),
                'CLISPH': to_driver_value(thermostat.changeable_values.heat_setpoint, True),
                'CLISPC': to_driver_value(thermostat.changeable_values.cool_setpoint, True),
                'CLIMD': modeMap[thermostat.changeable_values.mode],
                'CLIFS': fanMap[thermostat.settings.fan.changeable_values.mode],
                'CLIHUM': to_driver_value(thermostat.indoor_humidity, True),
                'CLIHCS': runningStateMap[thermostat.operation_status.mode],
                'CLIFRS': 1 if thermostat.operation_status.fan_request or thermostat.operation_status.circulation_fan_request else 0,  # This doesn't seem to work as expected
                'GV1': priorityTypeMap[thermostat.priority_type],
                'GV2': scheduleStatusMap[thermostat.schedule_status],
                'GV3': scheduleModeMap[thermostat.current_schedule_period.period] if thermostat.current_schedule_period.period in scheduleModeMap else scheduleModeMap['Custom'],
                'GV4': holdStatusMap[thermostat.changeable_values.thermostat_setpoint_status],
                'GV5': int(thermostat.vacation_hold.enabled),
                'GV6': int(thermostat.is_alive)
            }

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)
        except Exception as ex:
            self.l_error("_query", "Refreshing thermostat {0} failed {1}".format(self.address, ex))

        self.reportDrivers()

    def cmdSetPF(self, cmd):
        try:
            driver = cmd['cmd']

            # Get current values so we don't change the wrong things
            thermostat = self._api.get_thermostat(self._location_id, self._thermostat_id)
            h_setpoint = thermostat.changeable_values.heat_setpoint
            c_setpoint = thermostat.changeable_values.cool_setpoint
            mode = thermostat.changeable_values.mode
            auto_changeover_active = thermostat.changeable_values.auto_changeover_active

            updates = {
                'CLISPH': to_driver_value(h_setpoint, True),
                'CLISPC': to_driver_value(c_setpoint, True),
                'CLIMD': modeMap[mode],
            }

            if driver == 'CLISPH':
                self._api.set_setpoint(self._location_id, self._thermostat_id, cmd['value'], c_setpoint, self._use_celsius, mode, auto_changeover_active)
                updates['CLISPH'] = to_driver_value(cmd['value'], True)
            elif driver == 'CLISPC':
                self._api.set_setpoint(self._location_id, self._thermostat_id, h_setpoint, cmd['value'], self._use_celsius, mode, auto_changeover_active)
                updates['CLISPC'] = to_driver_value(cmd['value'], True)
            elif driver == 'CLIMD':
                mode = next((key for key, value in modeMap.items() if value == int(cmd['value'])), None)
                self._api.set_setpoint(self._location_id, self._thermostat_id, h_setpoint, c_setpoint, self._use_celsius, mode, auto_changeover_active)
                updates['CLIMD'] = cmd['value']

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)
        except Exception as ex:
            self.l_error("_setPF", "Could not set thermostat set point because {0}".format(self.address, ex))

    def cmdSetHoldStatus(self, cmd):
        try:
            # Get current values so we don't change the wrong things
            thermostat = self._api.get_thermostat(self._location_id, self._thermostat_id)
            h_setpoint = thermostat.changeable_values.heat_setpoint
            c_setpoint = thermostat.changeable_values.cool_setpoint
            mode = thermostat.changeable_values.mode
            auto_changeover_active = thermostat.changeable_values.auto_changeover_active

            updates = {}

            host_status_mode = setHoldStatusMap[int(cmd['value'])]
            self._api.set_setpoint(self._location_id, self._thermostat_id, h_setpoint, c_setpoint, self._use_celsius, mode, auto_changeover_active, host_status_mode)
            updates['GV4'] = cmd['value']

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)

        except Exception as ex:
            self.l_error("_setPF", "Could not set thermostat fan mode because {0}".format(self.address, ex))

    def cmdSetFS(self, cmd):
        try:
            updates = {}

            mode = next((key for key, value in fanMap.items() if value == int(cmd['value'])), None)
            self._api.set_fanmode(self._location_id, self._thermostat_id, mode)
            updates['CLIFS'] = cmd['value']

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)

        except Exception as ex:
            self.l_error("_setPF", "Could not set thermostat fan mode because {0}".format(self.address, ex))

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s: %s" % (self.id, self.address, self.name, name, string))

    commands = {
        'CLISPH': cmdSetPF,
        'CLISPC': cmdSetPF,
        'CLIMD': cmdSetPF,
        'GV4': cmdSetHoldStatus,
        'CLIFS': cmdSetFS,
    }
