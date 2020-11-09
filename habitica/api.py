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
    CONTENT_TYPE = 'application/json'
    URI_BASE = 'api/v3'
    TIMEOUT = 10.0

    def __init__(self, auth):
        """ Creates authenticated API instance. """
        self.auth = auth
        self.headers = auth if auth else {}
        self.headers.update({'content-type': API.CONTENT_TYPE})
    def get_url(self, *parts):
        """ Makes URL to call specified .../subpath/of/parts. """
        return '/'.join([self.auth['url'], API.URI_BASE] + list(parts))
    def call(self, method, uri, data):
        """ Performs actual call to URI using given method (POST/GET etc).
        Data should correspond to specified method.
        For POST/PUT methods, if field '_params' is present,
        it is extracted and passed as request params.
        """
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

MAX_RETRY = 3

def dump_errors(errors):
    for message in errors:
        print(message, file=sys.stderr)
    return None

class Habitica(object):
    """
    A minimalist Habitica API class.
    """

    def __init__(self, auth=None, resource=None, aspect=None, _api=None):
        self.api = _api or API(auth)
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
        return self.try_call(method, uri, kwargs)

    def try_call(self, method, uri, kwargs, tries=MAX_RETRY, messages=None):
        messages = messages or []
        if tries <= 0:
            return dump_errors(messages)
        # actually make the request of the API
        try:
            return self.actual_call(method, uri, kwargs)
        except requests.exceptions.ReadTimeout as e:
            messages.append(e)
            return self.try_call(method, uri, kwargs, tries - 1, messages=messages)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [502]:
                messages.append(e)
                return self.try_call(method, uri, kwargs, tries - 1, messages=messages)
            return dump_errors(messages + [e])
        except requests.exceptions.ConnectionError as e:
            return dump_errors(messages + [e])

    def actual_call(self, method, uri, kwargs):
        res = self.api.call(method, uri, kwargs)

        # print(res.url)  # debug...
        if res.status_code == requests.codes.ok:
            return res.json()['data']
        else:
            if res.status_code == 404:
                print('URI not found: {0}'.format(uri), file=sys.stderr)
            res.raise_for_status()
