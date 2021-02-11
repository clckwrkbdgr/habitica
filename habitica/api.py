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
from . import config

USER_ID_FILE = Path(pkg_resources.resource_filename('habitica', 'data/USER_ID'))
if not USER_ID_FILE.exists(): # pragma: no cover -- TODO duplicates code from setup.py. Needs to be moved to habitica.config and re-used.
    print('File {0} is missing.'.format(USER_ID_FILE))
    print('File {0} should be present in the root directory and should contain Habitica User ID of the author of the package.'.format(USER_ID_FILE))
    print('For forked project it is advisable to use your own User ID (see https://habitica.com/user/settings/api)')
    sys.exit(1)
USER_ID = USER_ID_FILE.read_text().strip()
if not re.match(r'^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$', USER_ID, flags=re.I): # pragma: no cover -- TODO see above
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

class Delay:
    """ Ensures specific interval between remote requests
    to reduce load on remote server.
    """
    def __init__(self, default_delay, **specific_method_delays):
        """ Sets default delay for request (in seconds).
        If any kwargs are given, they are treated as delays for specific methods,
        e.g.: (0.5, get=3, post=10)
        """
        self.default_delay = default_delay
        self.method_delays = {key.lower():value for key,value in specific_method_delays.items()}
        self._last_request_time = 0
    def wait_for(self, method):
        """ Stops execution until proper delay between requests is reached.
        May not freeze at all if last request was enough time ago.
        """
        delay = self.method_delays.get(method.lower(), self.default_delay)
        passed = (time.time() - self._last_request_time)
        logging.debug('Last request time: {0}, passed since then: {1}'.format(self._last_request_time, passed))
        logging.debug('Max delay: {0}'.format(delay))
        delay = delay - passed
        logging.debug('Actual delay: {0}'.format(delay))
        if delay > 0:
            time.sleep(delay)
    def update(self):
        """ Updates last request time.
        Should be called right after actual remote request.
        """
        self._last_request_time = time.time()

class API(object):
    """ Basic API facade. """
    TIMEOUT = 10.0 # Call timeout.
    MAX_RETRY = 3 # Amount of retries for server errors (5xx, timeouts etc).
    Delay = Delay

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

    class Cached: # pragma: no cover -- TODO uses external FS cache and invalidation by time.
        def __init__(self, api, cache_entry_name):
            self.api = api
            self.name = cache_entry_name
        def _cached_request(self, method, *args, **kwargs):
            cache_file = Path(config.get_cache_dir())/("{0}.cache.json".format(self.name))
            logging.debug("Using cache entry '{0}'".format(self.name))
            invalidated = not cache_file.exists() or time.time() > cache_file.stat().st_mtime + 60*60*24 # TODO how to invalidate Habitica content cache
            if invalidated and self.api._inside_response_hook:
                invalidated = False # Protection from direct API calls within response hook.
            if invalidated:
                logging.debug("Cache was invalid, making actual request...")
                data = getattr(self.api, method)(*args, **kwargs)
                cache_file.write_text(json.dumps(data))
            else:
                logging.debug("Cache was still valid, loading cached data...")
                data = dotdict(json.loads(cache_file.read_text()))
            return data
        def get(self, *args, **kwargs):
            return self._cached_request('get', *args, **kwargs)
        def post(self, *args, **kwargs):
            return self._cached_request('post', *args, **kwargs)
        def put(self, *args, **kwargs):
            return self._cached_request('put', *args, **kwargs)
        def delete(self, *args, **kwargs):
            return self._cached_request('delete', *args, **kwargs)
        def call(self, *args, **kwargs):
            return self._cached_request('call', *args, **kwargs)
        def __getattr__(self, attr):
            return getattr(self.api, attr)

    def __init__(self, base_url, login, password, batch_mode=True):
        """ Creates authenticated API instance.
        If batch_mode is True (default), introduces significant delays
        between consequent requests to reduce load on Habitica server.
        Otherwise (for user input) uses default nominal delay <1 sec.
        """
        self.base_url = base_url.rstrip('/')
        self.login = login
        self.password = password
        self.headers = {
              'x-api-user': login,
              'x-api-key': password,
              'x-client': USER_ID + '-habitica', # TODO take appName from package?
              'content-type': 'application/json',
              }
        self._response_hook = None
        self._inside_response_hook = False
        if batch_mode:
            # Third-party API tools should introduce delays between calls
            # to reduce load on Habitica server.
            # See https://habitica.fandom.com/wiki/Template:Third_Party_Tool_Rules?section=T-4
            self._delay = self.Delay(1,
                    get=3,
                    post=10, put=10, delete=10,
                    )
        else:
            self._delay = self.Delay(0.5)

    def cached(self, cache_entry_name): # pragma: no cover -- TODO see Cached class above.
        return API.Cached(self, cache_entry_name)

    def set_response_hook(self, hook_function): # pragma: no cover -- TODO
        """ Sets hook that accepts full response object
        and called for every successfull response.
        Response object (usually a dict) can be modified in-place.
        Return value is not checked.
        """
        self._response_hook = hook_function
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
        return self.call('POST', uri, body=_body, query=kwargs)
    def put(self, *path, _body=None, **kwargs):
        """ Convenience call for PUT /specified/sub/path/
        PUT fields should be passed as '_body={}'
        Other kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('PUT', uri, body=_body, query=kwargs)
    def delete(self, *path, **query):
        """ Convenience call for DELETE /specified/sub/path/
        Kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('DELETE', uri, query=query)
    def get(self, *path, _as_json=True, **query):
        """ Convenience call for GET /specified/sub/path/
        Kwargs are passed as query params.
        See call() for details.
        """
        uri = self.get_url(*path)
        return self.call('GET', uri, query=query, as_json=_as_json)
    def call(self, method, uri, query=None, body=None, as_json=True):
        """ Performs actual call to URI using given method (GET/POST/PUT/DELETE etc).
        Data should correspond to specified method.
        Query is a dict and is passed as query params.
        Body is a dict and is passed as body params (JSON-encoded).
        May raise exceptions from requests.
        May freeze for several seconds to ensure delay between requests
        (see POST_AUTO_REQUEST_DELAY, GET_AUTO_REQUEST_DELAY)
        """
        self._delay.wait_for(method)
        return self._retry_call(method, uri, query=query, body=body, as_json=as_json)
    def _retry_call(self, method, uri, query=None, body=None, as_json=True, tries=MAX_RETRY):
        try:
            logging.debug('Sending {0} {1}'.format(method.upper(), uri))
            logging.debug('Query: {0}'.format(query))
            logging.debug('Body: {0}'.format(body))
            return self._direct_call(method, uri, query=query, body=body, as_json=as_json)
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
        return self._retry_call(method, uri, query=query, body=body, as_json=as_json, tries=tries-1)
    def _direct_call(self, method, uri, query=None, body=None, as_json=True):
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
        self._delay.update()
        logging.debug('Answered: {0} {1}'.format(response.status_code, response.reason))
        if response.status_code != requests.codes.ok:
            logging.debug('Responded with error: {0}'.format(response.content))
            response.raise_for_status()
        if as_json:
            response = response.json()
        logging.debug('Response: {0}'.format(json.dumps(response, indent=2, sort_keys=True)))
        if self._response_hook and not self._inside_response_hook: # pragma: no cover -- TODO
            try:
                self._inside_response_hook = True
                self._response_hook(response)
            except:
                logging.exception('Exception in custom API response hook!')
            finally:
                self._inside_response_hook = False
        return dotdict(response)
