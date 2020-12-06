import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
from .. import core, api

class MockRequest:
	def __init__(self, method, path, response):
		self.method = method
		self.path = path
		self.response = api.dotdict(response)
		self.params = None
		self.body = None

class MockAPI:
	def __init__(self, *requests):
		self.base_url = 'http://localhost'
		self.requests = list(requests)
		self.responses = []
	def _perform_request(self, method, path, params=None, body=None):
		request = None
		for _ in self.requests:
			if _.method == method and list(_.path) == list(path):
				request = _
				break
		assert request is not None, "Expected request is not found in mock request chain: {0} /{1}".format(method.upper(), '/'.join(path))
		self.requests.remove(request)
		request.params = params
		request.body = body
		self.responses.append(request)
		return request.response
	def get(self, *path, **params):
		return self._perform_request('get', path, params=params)
	def post(self, *path, _body=None, **params):
		return self._perform_request('post', path, params=params, body=_body)
	def put(self, *path, _body=None, **params):
		return self._perform_request('put', path, params=params, body=_body)
	def delete(self, *path, **params):
		return self._perform_request('delete', path, params=params)

class TestBaseHabitica(unittest.TestCase):
	def should_get_home_url(self):
		habitica = core.Habitica(_api=MockAPI())
		self.assertEqual(habitica.home_url(), 'http://localhost/#/tasks')
	def should_detect_working_server(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['status'], {'data': {'status': 'up'}}),
			MockRequest('get', ['status'], {'data': {'status': ''}}),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertFalse(habitica.server_is_up())
