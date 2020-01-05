#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Phil Adams http://philadams.net

Python wrapper around the Habitica (http://habitica.com) API
http://github.com/philadams/habitica
"""


import sys
import json
import logging
logging.captureWarnings(True)

import requests
import requests.adapters
import urllib3
import urllib3.util.retry
logging.getLogger('urllib3.connectionpool').setLevel(logging.CRITICAL)

API_URI_BASE = 'api/v3'
API_CONTENT_TYPE = 'application/json'

TIMEOUT = 10.0
MAX_RETRY = 3

def dump_errors(errors):
    for message in errors:
        print(message, file=sys.stderr)
    return None

class Habitica(object):
    """
    A minimalist Habitica API class.
    """

    def __init__(self, auth=None, resource=None, aspect=None):
        self.auth = auth
        self.resource = resource
        self.aspect = aspect
        self.headers = auth if auth else {}
        self.headers.update({'content-type': API_CONTENT_TYPE})

    def __getattr__(self, m):
        try:
            return object.__getattr__(self, m)
        except AttributeError:
            if not self.resource:
                return Habitica(auth=self.auth, resource=m)
            else:
                return Habitica(auth=self.auth, resource=self.resource,
                                aspect=m)

    def __getitem__(self, m):
        try:
            return object.__getitem__(self, m)
        except AttributeError:
            if not self.resource:
                return Habitica(auth=self.auth, resource=m)
            else:
                res = self.resource + '/' + str(m)
                return Habitica(auth=self.auth, resource=res)

    def __call__(self, **kwargs):
        method = kwargs.pop('_method', 'get')

        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either i need to find a cleaner way here, or i should
        # get involved in the API itself and... help it.
        if self.aspect:
            aspect_id = kwargs.pop('_id', None)
            direction = kwargs.pop('_direction', None)
            if aspect_id is not None:
                uri = '%s/%s/%s/%s/%s' % (self.auth['url'],
                                          API_URI_BASE,
                                          self.resource,
                                          self.aspect,
                                          str(aspect_id))
            else:
                uri = '%s/%s/%s/%s' % (self.auth['url'],
                                       API_URI_BASE,
                                       self.resource,
                                       self.aspect)
            if direction is not None:
                uri = '%s/%s' % (uri, direction)
        else:
            uri = '%s/%s/%s' % (self.auth['url'],
                                API_URI_BASE,
                                self.resource)
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
        session = requests.Session()
        retries = urllib3.util.retry.Retry(total=5, backoff_factor=0.1)
        session.mount('https://', requests.adapters.HTTPAdapter(max_retries=retries))
        if method in ['put', 'post']:
            res = getattr(session, method)(uri, headers=self.headers,
                                            data=json.dumps(kwargs), timeout=TIMEOUT)
        else:
            res = getattr(session, method)(uri, headers=self.headers,
                                            params=kwargs, timeout=TIMEOUT)

        # print(res.url)  # debug...
        if res.status_code == requests.codes.ok:
            return res.json()['data']
        else:
            if res.status_code == 404:
                print('URI not found: {0}'.format(uri), file=sys.stderr)
            res.raise_for_status()
