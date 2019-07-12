#!/usr/bin/env python3

try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

import sys
import os

from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2 import OAuth2Token
from requests_oauthlib.oauth2_session import OAuth2Session
import honeywell_home
from honeywell_home.rest import ApiException

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super(Controller, self).__init__(polyglot)
        self.name = "Honeywell Home Controller"
        self.client_id = ""
        self.client_secret = ""
        self.user_id = ""
        self.api = None
        self.api_baseurl = "https://connectedhome-sandbox.apigee.net"
        self.auth_client = None
        self.oauth = None

        # Don't enable in deployed node server. I use these so I can run/debug directly in IntelliJ.
        LOGGER.debug("Profile Num: " + os.environ.get('PROFILE_NUM'))
        LOGGER.debug("MQTT Host: " + os.environ.get('MQTT_HOST'))
        LOGGER.debug("MQTT Port: " + os.environ.get('MQTT_PORT'))
        LOGGER.debug("Token: " + os.environ.get('TOKEN'))

    def start(self):
        LOGGER.info('Started Honeywell Home Nodeserver')
        if self.check_params():
            self.discover()
            self.setDriver('ST', 1)

    def shortPoll(self):
        pass

    def longPoll(self):
        self.query()

    def query(self):
        for node in self.nodes:
            if self.nodes[node] is not self:
                self.nodes[node].query()

            self.nodes[node].reportDrivers()

    def discover(self, *args, **kwargs):
        try:
            LOGGER.debug("Starting discovery")
            # If this is a re-discover than update=True
            update = len(args) > 0

            self.auth_client = BackendApplicationClient(client_id=self.client_id)
            self.oauth = OAuth2Session(client=self.auth_client)
            token = OAuth2Token(self.oauth.fetch_token(token_url='https://connectedhome-sandbox.apigee.net/oauth2/accesstoken',
                                           client_id=self.client_id,
                                           client_secret=self.client_secret))

            if token is None:
                LOGGER.error("Couldn't get token")

            configuration = honeywell_home.Configuration()
            configuration.access_token = token['access_token']
            configuration.host = 'https://connectedhome-sandbox.apigee.net'
            self.api = honeywell_home.DefaultApi(honeywell_home.ApiClient(configuration))

            locations = self.api.v2_locations_get(self.client_id, self.user_id)
            thermostats = self.api.v2_devices_thermostats_get(self.client_id, self.user_id, locations[0].location_id)
            sensors = self.api.v2_devices_thermostats_device_id_group_group_id_rooms_get(self.client_id, self.user_id, locations[0].location_id, thermostats[0].device_id, thermostats[0].groups[0].id)

            LOGGER.info("done")
        except Exception as ex:
            self.addNotice({'discovery_failed': 'Discovery failed please check logs for a more detailed error.'})
            LOGGER.error("Discovery failed with error {0}".format(ex))

    def delete(self):
        LOGGER.info('Honeywell Home NS Deleted')

    def stop(self):
        LOGGER.debug('Honeywell Home NS stopped.')

    def check_params(self):
        if 'client_id' in self.polyConfig['customParams']:
            self.client_id = self.polyConfig['customParams']['client_id']
        else:
            LOGGER.error('check_params: client_id not defined in customParams, please add it.  Using {}'.format(self.client_id))

        if 'client_secret' in self.polyConfig['customParams']:
            self.client_secret = self.polyConfig['customParams']['client_secret']
        else:
            LOGGER.error('check_params: client_secret not defined in customParams, please add it.  Using {}'.format(self.client_secret))

        if 'user_id' in self.polyConfig['customParams']:
            self.user_id = self.polyConfig['customParams']['user_id']
        else:
            LOGGER.error('check_params: user_id not defined in customParams, please add it.  Using {}'.format(self.user_id))

        # Make sure they are in the params
        self.addCustomParam({'client_id': self.client_id, 'client_secret': self.client_secret, "user_id": self.user_id})

        # Remove all existing notices
        self.removeNoticesAll()
        # Add a notice if they need to change the user/password from the default.
        if self.client_id == "" or self.client_secret == "" or self.user_id == "":
            self.addNotice({'mynotice': 'Please set proper client_id and client_secret in configuration page, and restart this nodeserver. See:<br />https://github.com/dbarentine/udi-honeywellhome-poly/blob/master/README.md'})
            return False
        else:
            return True

    def remove_notices_all(self,command):
        LOGGER.info('remove_notices_all:')
        # Remove all existing notices
        self.removeNoticesAll()

    def update_profile(self,command):
        LOGGER.info('update_profile:')
        st = self.poly.installprofile()
        return st

    id = 'controller'
    commands = {
        'DISCOVER': discover,
        'UPDATE_PROFILE': update_profile,
        'REMOVE_NOTICES_ALL': remove_notices_all
    }

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('HoneywellHome')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
