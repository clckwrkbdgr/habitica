import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
import json
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
		self._raises = []
	def raises(self, *exc_objects):
		self._raises = exc_objects
	def mount(self, *args, **kwargs): pass
	def _actual_call(self, method, args, kwargs):
		self._request = (method, args, kwargs)
		if self._raises:
			exc = self._raises[0]
			self._raises = self._raises[1:]
			raise exc
		return self._response
	def post(self, *args, **kwargs):
		return self._actual_call('post', args, kwargs)
	def put(self, *args, **kwargs):
		return self._actual_call('put', args, kwargs)
	def delete(self, *args, **kwargs):
		return self._actual_call('delete', args, kwargs)
	def get(self, *args, **kwargs):
		return self._actual_call('get', args, kwargs)
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
	def should_post_request(self):
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
					response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'post')
					self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
					self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
					self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_put_request(self):
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
					response = obj.put('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'put')
					self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
					self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
					self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_delete_request(self):
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
					response = obj.delete('path', 'to', 'request', query1='param1', query2='param2')
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'delete')
					self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
					self.assertEqual(json.loads(mock_session._request[2]['data']), {})
					self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_get_request(self):
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
					response = obj.get('path', 'to', 'request', query1='param1', query2='param2')
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'get')
					self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
					self.assertTrue('data' not in mock_session._request[2])
					self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_retry_on_occasional_exceptions(self):
		obj = api.API('http://localhost/', 'login', 'password')
		mock_time = unittest.mock.MagicMock(return_value=1)
		mock_sleep = unittest.mock.MagicMock()
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		mock_session.raises(
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ConnectionError(),
				)
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep):
				with unittest.mock.patch('requests.Session', mock_session):
					response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
					self.assertEqual(response, {'data':'test'})
					self.assertEqual(mock_session._request[0], 'post')
					self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
					self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
					self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_raise_on_endless_exceptions(self):
		obj = api.API('http://localhost/', 'login', 'password')
		mock_time = unittest.mock.MagicMock(return_value=1)
		mock_sleep = unittest.mock.MagicMock()
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		mock_session.raises(
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ConnectionError(),
				requests.exceptions.ConnectionError(),
				requests.exceptions.ConnectionError(),
				requests.exceptions.ConnectionError(),
				)
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep):
				with unittest.mock.patch('requests.Session', mock_session):
					with self.assertRaises(requests.exceptions.ReadTimeout):
						response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
					with self.assertRaises(requests.exceptions.ConnectionError):
						response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
	def should_raise_on_http_errors(self):
		obj = api.API('http://localhost/', 'login', 'password')
		mock_time = unittest.mock.MagicMock(return_value=1)
		mock_sleep = unittest.mock.MagicMock()
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=404,
			content={'data':'test'},
			))
		real_response = requests.Response
		real_response.status_code = 404
		mock_session.raises(
				requests.exceptions.HTTPError(response=real_response),
				)
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep):
				with unittest.mock.patch('requests.Session', mock_session):
					with self.assertRaises(requests.exceptions.HTTPError):
						response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
	def should_retry_on_appserver_http_errors(self):
		obj = api.API('http://localhost/', 'login', 'password')
		mock_time = unittest.mock.MagicMock(return_value=1)
		mock_sleep = unittest.mock.MagicMock()
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=502,
			content={'data':'test'},
			))
		real_response = requests.Response
		real_response.status_code = 502
		mock_session.raises(
				requests.exceptions.HTTPError(response=real_response),
				requests.exceptions.HTTPError(response=real_response),
				requests.exceptions.HTTPError(response=real_response),
				requests.exceptions.HTTPError(response=real_response),

				requests.exceptions.HTTPError(response=real_response),
				)
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep):
				with unittest.mock.patch('requests.Session', mock_session):
					with self.assertRaises(requests.exceptions.HTTPError):
						response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})

					response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
					self.assertEqual(response, {'data':'test'})
