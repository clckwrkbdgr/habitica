#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import logging
logging.captureWarnings(True)
import requests
import requests.adapters
import urllib3
import urllib3.util.retry
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

class API(object):
    """ Basic API facade. """
    TIMEOUT = 10.0 # Call timeout.
    MAX_RETRY = 3 # Amount of retries for server errors (5xx, timeouts etc).

    def __init__(self, base_url, login, password):
        """ Creates authenticated API instance. """
        self.base_url = base_url
        self.login = login
        self.password = password
        self.headers = {
              'x-api-user': login,
              'x-api-key': password,
              'content-type': 'application/json',
              }
    def get_url(self, *parts):
        """ Makes URL to call specified .../subpath/of/parts. """
        return '/'.join([self.base_url, 'api', 'v3'] + list(parts))
    def call(self, method, uri, data):
        """ Performs actual call to URI using given method (POST/GET etc).
        Data should correspond to specified method.
        For POST/PUT methods, if field '_params' is present,
        it is extracted and passed as request params.
        May raise exceptions from requests.
        """
        return self._retry_call(method, uri, data)
    def _retry_call(self, method, uri, data, tries=MAX_RETRY):
        try:
            return self._direct_call(method, uri, data)
        except requests.exceptions.ReadTimeout as e:
            if tries <= 0:
                raise
        except requests.exceptions.HTTPError as e:
            if e.response.status_code not in [502]:
                raise
            if tries <= 0:
                raise
        except requests.exceptions.ConnectionError as e:
            if tries <= 0:
                raise
        return self._retry_call(method, uri, data, tries=tries-1)
    def _direct_call(self, method, uri, data):
        """ Direct call without any retry/timeout checks. """
        session = requests.Session()
        retries = urllib3.util.retry.Retry(total=5, backoff_factor=0.1)
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

        if method in ['put', 'post']:
            params = data.get('_params', None)
            if '_params' in data:
                del data['_params']
            return getattr(session, method)(uri, headers=self.headers,
                    params=params, data=json.dumps(data), timeout=API.TIMEOUT)
        else:
            return getattr(session, method)(uri, headers=self.headers,
                                            params=data, timeout=API.TIMEOUT)

class Habitica(object):
    """
    A minimalist Habitica API class.
    """

    def __init__(self, auth=None, resource=None, aspect=None, _api=None):
        self.api = _api or API(auth['url'], auth['x-api-user'], auth['x-api-key'])
        self.resource = resource
        self.aspect = aspect

    def __getattr__(self, m):
        try:
            return object.__getattr__(self, m)
        except AttributeError:
            if not self.resource:
                return Habitica(_api=self.api, resource=m)
            else:
                return Habitica(_api=self.api, resource=self.resource,
                                aspect=m)

    def __getitem__(self, m):
        try:
            return object.__getitem__(self, m)
        except AttributeError:
            if not self.resource:
                return Habitica(_api=self.api, resource=m)
            else:
                res = self.resource + '/' + str(m)
                return Habitica(_api=self.api, resource=res)

    def __call__(self, **kwargs):
        method = kwargs.pop('_method', 'get')

        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either i need to find a cleaner way here, or i should
        # get involved in the API itself and... help it.
        if self.aspect:
            aspect_id = kwargs.pop('_id', None)
            direction = kwargs.pop('_direction', None)
            if aspect_id is not None:
                uri = self.api.get_url(
                                          self.resource,
                                          self.aspect,
                                          str(aspect_id))
            else:
                uri = self.api.get_url(
                                       self.resource,
                                       self.aspect)
            if direction is not None:
                uri = '%s/%s' % (uri, direction)
        else:
            uri = self.api.get_url(self.resource)

        try:
            res = self.api.call(method, uri, kwargs)
        except:
            logging.exception('Failed to perform API call {0} {1} <= {2}'.format(method.upper(), uri, kwargs))
            return None
        if not res:
            return res

        logging.debug(res.url)
        if res.status_code == requests.codes.ok:
            return res.json()['data']
        else:
            if res.status_code == 404:
                logging.error('URI not found: {0}'.format(uri), file=sys.stderr)
            res.raise_for_status()
