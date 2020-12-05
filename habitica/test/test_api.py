import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
import requests
from .. import api

class TestUtils(unittest.TestCase):
	def should_access_dotdict_fields_via_dot(self):
		d = api.dotdict()
		d['field'] = 'foo'
		self.assertEqual(d.field, 'foo')
		self.assertEqual(d['field'], 'foo')
	def should_create_dotdict_from_base_dict(self):
		d = api.dotdict({'field':'foo'})
		self.assertEqual(d.field, 'foo')
		self.assertEqual(d['field'], 'foo')
	def should_set_dotdict_fields_via_dot(self):
		d = api.dotdict({'field':'foo'})
		d.field = 'foo'
		self.assertEqual(d.field, 'foo')
		self.assertEqual(d['field'], 'foo')
	def should_convert_nested_dicts_to_dotdicts(self):
		d = api.dotdict({'field':'foo', 'nested' : {'subfield': 'bar'}})
		self.assertEqual(d.field, 'foo')
		self.assertEqual(d.nested.subfield, 'bar')

class MyException(api.API.Exception):
	CODE, MESSAGE = 404, 'My object was not found'

class TestExceptionConversions(unittest.TestCase):
	def should_reraise_unknown_exception(self):
		with self.assertRaises(requests.exceptions.HTTPError) as e:
			with api.API.Exceptions(MyException):
				response = requests.Response()
				response.status_code = 401
				response._content = b'Not Authorized to use this exception'
				raise requests.exceptions.HTTPError(response=response)
		self.assertEqual(e.exception.response.status_code, 401)
		self.assertEqual(e.exception.response.text, 'Not Authorized to use this exception')
	def should_convert_known_exception(self):
		with self.assertRaises(MyException) as e:
			with api.API.Exceptions(MyException):
				response = requests.Response()
				response.status_code = 404
				response._content = b'Text for My object was not found'
				raise requests.exceptions.HTTPError(response=response)
		self.assertEqual(e.exception.CODE, 404)
		self.assertEqual(str(e.exception), 'My object was not found')

class MockRequestSession:
	class Response:
		def __init__(self, status_code=None, reason=None, content=None):
			self.status_code = status_code
			self.reason = reason
			self.content = content
		def json(self):
			return self.content
		def raise_for_status(self):
			pass

	def __init__(self, response):
		self._response = response

	def mount(self, *args, **kwargs): pass
	def post(self, *args, **kwargs):
		self._request = ('post', args, kwargs)
		return self._response
	def put(self, *args, **kwargs):
		self._request = ('put', args, kwargs)
		return self._response
	def delete(self, *args, **kwargs):
		self._request = ('delete', args, kwargs)
		return self._response
	def get(self, *args, **kwargs):
		self._request = ('get', args, kwargs)
		return self._response
	def __call__(self, *args, **kwargs):
		return self

class TestAPI(unittest.TestCase):
	def should_fill_request_headers(self):
		obj = api.API('http://localhost/', 'login', 'password')
		self.assertEqual(obj.headers['x-api-user'], 'login')
		self.assertEqual(obj.headers['x-api-key'], 'password')
		self.assertEqual(obj.headers['x-client'], api.USER_ID + '-habitica')
		self.assertEqual(obj.headers['content-type'], 'application/json')
	def should_create_target_url(self):
		obj = api.API('http://localhost/', 'login', 'password')
		self.assertEqual(obj.get_url('sample', 'request'), 'http://localhost/api/v3/sample/request')
	def should_perform_a_call(self):
		obj = api.API('http://localhost/', 'login', 'password')
		mock_time = unittest.mock.MagicMock(return_value=1)
		mock_sleep = unittest.mock.MagicMock()
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep):
				with unittest.mock.patch('requests.Session', mock_session):
					response = obj.call('post', obj.get_url('sample'))
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'post')
