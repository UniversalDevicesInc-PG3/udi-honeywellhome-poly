try:
    import polyinterface
except ImportError:
    import pgc_interface as polyinterface

import honeywell_home
from honeywell_home.rest import ApiException
from retry import retry
from oauthlib.openid.connect.core.exceptions import InvalidTokenError

from oauthlib.oauth2 import BackendApplicationClient
from oauthlib.oauth2 import OAuth2Token
from requests_oauthlib.oauth2_session import OAuth2Session
from urllib.parse import urljoin

LOGGER = polyinterface.LOGGER


class ApiHelper:
    def __init__(self, api_baseurl, client_id, client_secret, user_id):
        self._api_baseurl = api_baseurl
        self._client_id = client_id
        self._client_secret = client_secret
        self._user_id = user_id
        self._auth_client = BackendApplicationClient(client_id=self._client_id)
        self._oauth = OAuth2Session(client=self._auth_client)

        configuration = honeywell_home.Configuration()
        configuration.host = self._api_baseurl
        configuration.access_token = None
        self._api = honeywell_home.DefaultApi(honeywell_home.ApiClient(configuration))

    def get_locations(self):
        return self._call_api(lambda: self._api.v2_locations_get(self._client_id, self._user_id))

    def get_thermostats(self, location_id):
        return self._call_api(lambda: self._api.v2_devices_thermostats_get(self._client_id, self._user_id, location_id))

    def get_sensors(self, location_id, thermostat_id, group_id):
        return self._call_api(lambda: self._api.v2_devices_thermostats_device_id_group_group_id_rooms_get(self._client_id, self._user_id, location_id, thermostat_id, group_id))

    @retry(InvalidTokenError, tries=3)
    def _call_api(self, function):
        try:
            if self._api.api_client.configuration.access_token is None:
                self._refresh_token()

            return function()
        except ApiException as ex:
            if ex.status == 401:
                self._api.api_client.configuration.access_token = None
                raise InvalidTokenError(status_code=ex.status, description=ex.reason)

            raise

    def _refresh_token(self):
        url = urljoin(self._api_baseurl, "oauth2/accesstoken")
        token = OAuth2Token(self._oauth.fetch_token(token_url=url,
                                                          client_id=self._client_id,
                                                          client_secret=self._client_secret))

        self._api.api_client.configuration.access_token = token['access_token']
