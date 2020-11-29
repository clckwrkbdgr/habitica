#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json, re
import time
import logging
import contextlib
import pkg_resources
from pathlib import Path
logging.captureWarnings(True)
import requests
import requests.adapters
import urllib3
import urllib3.util.retry
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

USER_ID_FILE = Path(pkg_resources.resource_filename('habitica', 'data/USER_ID'))
if not USER_ID_FILE.exists(): # TODO duplicates code from setup.py. Needs to be moved to habitica.config and re-used.
    print('File {0} is missing.'.format(USER_ID_FILE))
    print('File {0} should be present in the root directory and should contain Habitica User ID of the author of the package.'.format(USER_ID_FILE))
    print('For forked project it is advisable to use your own User ID (see https://habitica.com/user/settings/api)')
    sys.exit(1)
USER_ID = USER_ID_FILE.read_text().strip()
if not re.match(r'^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$', USER_ID, flags=re.I):
    print('File {0} contains invalid user_id: {1}'.format(USER_ID_FILE, repr(USER_ID)))
    print('Please ensure that proper User ID is used (see https://habitica.com/user/settings/api)')
    sys.exit(1)

class dotdict(dict):
    """ Dict that support dotted access:
      d['value']['nested_value'] == d.value.nested_value

    <https://stackoverflow.com/a/23689767/2128769>
    """
    def __getattr__(self, attr):
        value = dict.get(self, attr)
        return dotdict(value) if type(value) is dict else value
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class API(object):
    """ Basic API facade. """
    TIMEOUT = 10.0 # Call timeout.
    MAX_RETRY = 3 # Amount of retries for server errors (5xx, timeouts etc).

    # Third-party API tools should introduce delays between calls
    # to reduce load on Habitica server.
    # See https://habitica.fandom.com/wiki/Template:Third_Party_Tool_Rules?section=T-4
    DEFAULT_REQUEST_DELAY = 0.5 # sec
    GET_AUTO_REQUEST_DELAY = 3 # sec
    POST_AUTO_REQUEST_DELAY = 10 # sec

    class Exception(Exception):
        """ Basic API exception.
        Matches HTTP error code with specified message.
        Subclasses should have these fields redefined:
        >>> class MyException(API.Exception):
        ...     CODE, MESSAGE = 404, 'My object was not found.'
        """
        CODE = None
        MESSAGE = None
        def __str__(self): return self.MESSAGE

    @contextlib.contextmanager
    def Exceptions(*exceptions):
        """ Context manager to capture and convert HTTP errors
        to known API exceptions. All other exceptions will be re-raised.
        Exceptions should be subclasses of API.Exception
        and are matched by class field CODE. See API.Exception for details.
        Being a proper context manager, can be also used as function decorator.
        >>> with API.Exceptions(ValidationFailed, ObjectNotFound):
        ...     return api.call(...)
        """
        try:
            yield
        except requests.exceptions.HTTPError as e:
            for exc in exceptions:
                if exc.CODE == e.response.status_code:
                    raise exc()
            raise

    def __init__(self, base_url, login, password, batch_mode=True):
        """ Creates authenticated API instance.
        If batch_mode is True (default), introduces significant delays
        between consequent requests to reduce load on Habitica server.
        Otherwise (for user input) uses default nominal delay <1 sec.
        """
        self.batch_mode = batch_mode
        self.base_url = base_url
        self.login = login
        self.password = password
        self.headers = {
              'x-api-user': login,
              'x-api-key': password,
              'x-client': USER_ID + '-habitica', # TODO take appName from package?
              'content-type': 'application/json',
              }
        self._last_request_time = 0
    def get_url(self, *parts):
        """ Makes URL to call specified .../subpath/of/parts. """
        return '/'.join([self.base_url, 'api', 'v3'] + list(parts))
    def post(self, *path, _body=None, **kwargs):
        """ Convenience call for POST /specified/sub/path/
        POST fields should be passed as '_body={}'
        Other kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('POST', uri, body=kwargs)
    def put(self, *path, _body=None, **kwargs):
        """ Convenience call for PUT /specified/sub/path/
        PUT fields should be passed as '_body={}'
        Other kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('PUT', uri, body=kwargs)
    def delete(self, *path, **query):
        """ Convenience call for DELETE /specified/sub/path/
        Kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('DELETE', uri, query=query)
    def get(self, *path, **query):
        """ Convenience call for GET /specified/sub/path/
        Kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('GET', uri, query=query)
    def call(self, method, uri, query=None, body=None):
        """ Performs actual call to URI using given method (GET/POST/PUT/DELETE etc).
        Data should correspond to specified method.
        Query is a dict and is passed as query params.
        Body is a dict and is passed as body params (JSON-encoded).
        May raise exceptions from requests.
        May freeze for several seconds to ensure delay between requests
        (see POST_AUTO_REQUEST_DELAY, GET_AUTO_REQUEST_DELAY)
        """
        if not self.batch_mode:
            delay = self.DEFAULT_REQUEST_DELAY
        elif method.upper() in ['PUT', 'POST', 'DELETE']:
            delay = self.POST_AUTO_REQUEST_DELAY
        else:
            delay = self.GET_AUTO_REQUEST_DELAY
        passed = (time.time() - self._last_request_time)
        logging.debug('Last request time: {0}, passed since then: {1}'.format(self._last_request_time, passed))
        logging.debug('Max delay: {0}'.format(delay))
        delay = delay - passed
        logging.debug('Actual delay: {0}'.format(delay))
        if delay > 0:
            time.sleep(delay)
        return self._retry_call(method, uri, query=query, body=body)
    def _retry_call(self, method, uri, query=None, body=None, tries=MAX_RETRY):
        try:
            logging.debug('Sending {0} {1}'.format(method.upper(), uri))
            logging.debug('Query: {0}'.format(query))
            logging.debug('Body: {0}'.format(body))
            return self._direct_call(method, uri, query=query, body=body)
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
        return self._retry_call(method, uri, query=query, body=body, tries=tries-1)
    def _direct_call(self, method, uri, query=None, body=None):
        """ Direct call without any retry/timeout checks. """
        session = requests.Session()
        retries = urllib3.util.retry.Retry(total=5, backoff_factor=0.1)
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))

        if method.upper() in ['PUT', 'POST', 'DELETE']:
            response = getattr(session, method.lower())(uri, headers=self.headers,
                    params=query, data=json.dumps(body or {}), timeout=API.TIMEOUT)
        else:
            response = getattr(session, method.lower())(uri, headers=self.headers,
                                            params=query, timeout=API.TIMEOUT)
        self._last_request_time = time.time()
        logging.debug('Answered: {0} {1}'.format(response.status_code, response.reason))
        if response.status_code != requests.codes.ok:
            logging.debug('Responded with error: {0}'.format(response.content))
            response.raise_for_status()
        response = response.json()
        logging.debug('Response: {0}'.format(json.dumps(response, indent=2, sort_keys=True)))
        return dotdict(response)

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
            params = kwargs.get('_params', None)
            if '_params' in kwargs:
                del kwargs['_params']
            res = self.api.call(method, uri, query=kwargs, body=params)
            logging.debug('Response URL: {0}'.format(res.url))
            return res.data
        except requests.exceptions.HTTPError:
            raise
        except:
            logging.exception('Failed to perform API call {0} {1} <= {2}'.format(method.upper(), uri, kwargs))
            return None
