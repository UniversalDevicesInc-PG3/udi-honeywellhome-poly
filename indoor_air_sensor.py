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
    'HwhSensorF': [
        {'driver': 'GV0', 'value': 0, 'uom': '25'},  # Status
        {'driver': 'ST', 'value': 0, 'uom': '17'},
        {'driver': 'GV1', 'value': 0, 'uom': '17'},  # Avg Temp
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'},
        {'driver': 'GV2', 'value': 0, 'uom': '22'},  # Avg Humidity
        {'driver': 'GV3', 'value': int(False), 'uom': '2'},  # Motion
        {'driver': 'GV4', 'value': int(False), 'uom': '2'},  # Occupancy
        {'driver': 'GV5', 'value': 0, 'uom': '25'},  # Battery Status
    ],
    'HwhSensorC': [
        {'driver': 'GV0', 'value': 0, 'uom': '25'},  # Status
        {'driver': 'ST', 'value': 0, 'uom': '17'},
        {'driver': 'GV1', 'value': 0, 'uom': '17'},  # Avg Temp
        {'driver': 'CLIHUM', 'value': 0, 'uom': '22'},
        {'driver': 'GV2', 'value': 0, 'uom': '22'},  # Avg Humidity
        {'driver': 'GV3', 'value': int(False), 'uom': '2'},  # Motion
        {'driver': 'GV4', 'value': int(False), 'uom': '2'},  # Occupancy
        {'driver': 'GV5', 'value': 0, 'uom': '25'},  # Battery Status
    ]
}

sensorStatusMap = {
    'Unknown': 0,
    'Ok': 1,
    'NotAvailable': 2,
}

sensorBatteryStatusMap = {
    'Unknown': 0,
    'Ok': 1,
    'Low': 2,
}


class IndoorAirSensor(polyinterface.Node):

    def __init__(self, controller, primary, address, name, api, location_id, thermostat_id, group_id, sensor_id, is_celsius):
        self.controller = controller
        self._api = api
        self._location_id = location_id
        self._thermostat_id = thermostat_id
        self._group_id = group_id
        self._sensor_id = sensor_id
        self._use_celsius = is_celsius
        self.type = 'sensor'
        self.id = 'HwhSensorF' if self._use_celsius else 'HwhSensorF'
        self.drivers = self._convertDrivers(driversMap[self.id]) if CLOUD else deepcopy(driversMap[self.id])

        super(IndoorAirSensor, self).__init__(controller, primary, address, name)

    def start(self):
        self.query()

    def query(self):
        try:
            LOGGER.debug("Query sensor {}".format(self.address))
            sensors = self._api.get_sensors(self._location_id, self._thermostat_id, self._group_id)

            sensor = next((s for s in sensors.rooms if s.id == self._sensor_id), None)

            if sensor is None:
                LOGGER.error("Sensor {0} in group {1} doesn't exist".format(self.address, self._group_id))
                self.addNotice({'mynotice': "Sensor {0} in group {1} doesn't exist. Unable to refresh sensor data.".format(self.address, self._group_id)})
                return

            # TODO: Do we ever have to care about multiple accessory blocks?
            # We know at least one block exists otherwise the indoor_air_sensor wouldn't have been added
            sensor_accessories = sensor.accessories[0]
            updates = {
                'GV0': sensorStatusMap[sensor_accessories.accessory_value.status] if sensor_accessories.accessory_value.status in sensorStatusMap else sensorStatusMap['Unknown'],
                'ST': to_driver_value(sensor_accessories.accessory_value.indoor_temperature, False),
                'GV1': to_driver_value(sensor.avg_temperature, False),
                'CLIHUM': to_driver_value(sensor_accessories.accessory_value.indoor_humidity, True),
                'GV2': to_driver_value(sensor.avg_humidity, True),
                'GV3': int(sensor_accessories.accessory_value.motion_det),
                'GV4': int(sensor_accessories.accessory_value.occupancy_det),
                'GV5': sensorBatteryStatusMap[sensor_accessories.accessory_value.battery_status] if sensor_accessories.accessory_value.battery_status in sensorBatteryStatusMap else sensorBatteryStatusMap['Unknown'],
            }

            for key, value in updates.items():
                self.l_debug('_update', 'setDriver({},{})'.format(key, value))
                self.setDriver(key, value)

        except Exception as ex:
            LOGGER.exception("Could not refreshing indoor air sensor %s because %s", self.address, ex)

        self.reportDrivers()

    def l_debug(self, name, string):
        LOGGER.debug("%s:%s:%s:%s: %s" % (self.id, self.address, self.name, name, string))
