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
    'NotSupported': 0,
    'PickARoom': 1,
    'FollowMe': 2,
    'WholeHouse': 3
}

scheduleStatusMap = {
    'Pause': 0,
    'Resume': 1
}

scheduleModeMap = {
    'NotSupported': 0,
    'Wake': 1,
    'Away': 2,
    'Home': 3,
    'Sleep': 4,
    'Custom': 5
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
                'GV1': priorityTypeMap['NotSupported'],
                'GV2': scheduleStatusMap[thermostat.schedule_status],
                'GV3': scheduleModeMap['NotSupported'],
                'GV4': holdStatusMap[thermostat.changeable_values.thermostat_setpoint_status],
                'GV5': False,
                'GV6': int(thermostat.is_alive)
            }

            if thermostat.priority_type is not None:
                updates['GV1'] = priorityTypeMap[thermostat.priority_type]

            if thermostat.current_schedule_period is not None:
                updates['GV3'] = scheduleModeMap[thermostat.current_schedule_period.period] if thermostat.current_schedule_period.period in scheduleModeMap else scheduleModeMap['Custom']

            if thermostat.vacation_hold is not None:
                updates['GV5'] = int(thermostat.vacation_hold.enabled)

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)
        except Exception as ex:
            LOGGER.exception("Refreshing thermostat %s failed %s", self.address, ex)

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
            next_period_time = thermostat.changeable_values.next_period_time

            updates = {
                'CLISPH': to_driver_value(h_setpoint, True),
                'CLISPC': to_driver_value(c_setpoint, True),
                'CLIMD': modeMap[mode],
            }

            if driver == 'CLISPH':
                # There is a bug in the API when setting heat point. Basically TemporaryHold doesn't work.
                # So instead we need to use HoldUntil with next period time which is essentially the same thing.
                self._api.set_setpoint(self._location_id, self._thermostat_id, cmd['value'], c_setpoint, self._use_celsius, mode, auto_changeover_active, "HoldUntil", next_period_time)
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
            LOGGER.exception("Could not set thermostat set point %s because %s", self.address, ex)

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
            LOGGER.exception("Could not set thermostat hold status %s because %s", self.address, ex)

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
            LOGGER.exception("Could not set thermostat fan mode %s because %s", self.address, ex)

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s: %s" % (self.id, self.address, self.name, name, string))

    commands = {
        'CLISPH': cmdSetPF,
        'CLISPC': cmdSetPF,
        'CLIMD': cmdSetPF,
        'GV4': cmdSetHoldStatus,
        'CLIFS': cmdSetFS,
    }
