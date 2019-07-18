try:
    import polyinterface

    CLOUD = False
except ImportError:
    import pgc_interface as polyinterface

    CLOUD = True

from copy import deepcopy

LOGGER = polyinterface.LOGGER

driversMap = {
    'HwhF': [
        {'driver': 'ST', 'value': 0, 'uom': '17'},
        {'driver': 'CLISPH', 'value': 0, 'uom': '17'},
        {'driver': 'CLISPC', 'value': 0, 'uom': '17'},
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'}
    ],
    'HwhC': [
        {'driver': 'ST', 'value': 0, 'uom': '4'},
        {'driver': 'CLISPH', 'value': 0, 'uom': '4'},
        {'driver': 'CLISPC', 'value': 0, 'uom': '4'},
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'}
    ]
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
                'ST': self.tempToDriver(thermostat.indoor_temperature, True, False),
                'CLISPH': self.tempToDriver(thermostat.changeable_values.heat_setpoint, True),
                'CLISPC': self.tempToDriver(thermostat.changeable_values.cool_setpoint, True),
                'CLIHUM': thermostat.indoor_humidity
            }

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)
        except Exception as ex:
            self.l_error("_query", "Refreshing thermostat {0} failed {1}".format(self.address, ex))

        self.reportDrivers()

    # Convert Temperature for driver
    # FromE converts from Ecobee API value, and to C if necessary
    # By default F values are converted to int, but for ambiant temp we
    # allow one decimal.
    def tempToDriver(self, temp, fromE=False, FtoInt=True):
        try:
            temp = float(temp)
        except:
            LOGGER.error("{}:tempToDriver: Unable to convert '{}' to float")
            return False
        # Convert from Ecobee value, unless it's already 0.
        if fromE and temp != 0:
            temp = temp / 10
        if self._use_celsius:
            if fromE:
                temp = self.toC(temp)
            return temp
        else:
            if FtoInt:
                return int(temp)
            else:
                return temp

    def toC(tempF):
        # Round to the nearest .5
        return round(((tempF - 32) / 1.8) * 2) / 2

    def toF(tempC):
        # Round to nearest whole degree
        return int(round(tempC * 1.8) + 32)

    def l_info(self, name, string):
        LOGGER.info("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_error(self, name, string):
        LOGGER.error("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_warning(self, name, string):
        LOGGER.warning("%s:%s:%s: %s" % (self.id, self.name, name, string))

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s: %s" % (self.id, self.address, self.name, name, string))

    commands = {
    }
