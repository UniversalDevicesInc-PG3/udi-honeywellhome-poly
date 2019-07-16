try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

LOGGER = polyinterface.LOGGER


class Thermostat(polyinterface.Node):

    def __init__(self, controller, primary, address, name, api, thermostat_id):
        super(Thermostat, self).__init__(controller, primary, address, name)
        self.api = api
        self.thermostat_id = thermostat_id

    def start(self):
        self.query()

    def query(self):
        self.reportDrivers()

    drivers = [
    ]

    id = 'hw_t'
    commands = {
    }
