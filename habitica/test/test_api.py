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

class TestDelay(unittest.TestCase):
	def should_perform_first_call_immediately(self):
		mock_time = unittest.mock.MagicMock(return_value=1000)
		mock_sleep = unittest.mock.MagicMock()
		delay = api.Delay(3)
		with unittest.mock.patch('time.time', mock_time):
			with unittest.mock.patch('time.sleep', mock_sleep) as sleep:
				delay.wait_for('get')
				self.assertFalse(sleep.called)
	def should_wait_for_the_second_call(self):
		mock_time = unittest.mock.MagicMock(return_value=1000)
		mock_sleep = unittest.mock.MagicMock()
		delay = api.Delay(1, get=3, post=10)
		with unittest.mock.patch('time.time', mock_time) as get_time:
			with unittest.mock.patch('time.sleep', mock_sleep) as sleep:
				delay.wait_for('get')
				get_time.return_value = 1001
				delay.update()
				get_time.return_value = 1003
				delay.wait_for('get')
				sleep.assert_called_with(1)
	def should_wait_longer_for_the_second_call_for_post_requests(self):
		mock_time = unittest.mock.MagicMock(return_value=1000)
		mock_sleep = unittest.mock.MagicMock()
		delay = api.Delay(1, get=3, post=10)
		with unittest.mock.patch('time.time', mock_time) as get_time:
			with unittest.mock.patch('time.sleep', mock_sleep) as sleep:
				delay.wait_for('post')
				get_time.return_value = 1001
				delay.update()
				get_time.return_value = 1003
				delay.wait_for('post')
				sleep.assert_called_with(8)
	def should_wait_the_default_amount_when_no_methods_are_specified(self):
		mock_time = unittest.mock.MagicMock(return_value=1000)
		mock_sleep = unittest.mock.MagicMock()
		delay = api.Delay(0.5)
		with unittest.mock.patch('time.time', mock_time) as get_time:
			with unittest.mock.patch('time.sleep', mock_sleep) as sleep:
				delay.wait_for('get')
				get_time.return_value = 1001
				delay.update()
				get_time.return_value = 1001.1
				delay.wait_for('get')
				self.assertAlmostEqual(sleep.call_args[0][0], 0.4)
				get_time.return_value = 1001.5
				delay.update()
				get_time.return_value = 1001.7
				delay.wait_for('post')
				self.assertAlmostEqual(sleep.call_args[0][0], 0.3)

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

class MockDelay:
	def __init__(self, *args, **kwargs):
		self.args = args
		self.kwargs = kwargs
		self.waited_for = []
		self.updated = False
	def wait_for(self, method):
		self.waited_for.append(method)
		self.updated = False
	def update(self):
		self.updated = True

class MockAPI(api.API):
	Delay = MockDelay

class TestAPI(unittest.TestCase):
	def should_fill_request_headers(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		self.assertEqual(obj.headers['x-api-user'], 'login')
		self.assertEqual(obj.headers['x-api-key'], 'password')
		self.assertEqual(obj.headers['x-client'], api.USER_ID + '-habitica')
		self.assertEqual(obj.headers['content-type'], 'application/json')
	def should_create_target_url(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		self.assertEqual(obj.get_url('sample', 'request'), 'http://localhost/api/v3/sample/request')
	def should_perform_a_call(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.call('post', obj.get_url('sample'))
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'post')
			self.assertEqual(obj._delay.waited_for, ['post'])
			self.assertTrue(obj._delay.updated)
	def should_post_request(self):
		obj = MockAPI('http://localhost/', 'login', 'password', batch_mode=False)
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'post')
			self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
			self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
			self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_put_request(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.put('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'put')
			self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
			self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
			self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_delete_request(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.delete('path', 'to', 'request', query1='param1', query2='param2')
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'delete')
			self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
			self.assertEqual(json.loads(mock_session._request[2]['data']), {})
			self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_get_request(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.get('path', 'to', 'request', query1='param1', query2='param2')
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'get')
			self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
			self.assertTrue('data' not in mock_session._request[2])
			self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_retry_on_occasional_exceptions(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=200,
			content={'data':'test'},
			))
		mock_session.raises(
				requests.exceptions.ReadTimeout(),
				requests.exceptions.ConnectionError(),
				)
		with unittest.mock.patch('requests.Session', mock_session):
			response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
			self.assertEqual(response, {'data':'test'})
			self.assertEqual(mock_session._request[0], 'post')
			self.assertEqual(mock_session._request[1], ('http://localhost/api/v3/path/to/request',))
			self.assertEqual(json.loads(mock_session._request[2]['data']), {'request':'value'})
			self.assertEqual(mock_session._request[2]['params'], {'query1':'param1', 'query2':'param2'})
	def should_raise_on_endless_exceptions(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
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
		with unittest.mock.patch('requests.Session', mock_session):
			with self.assertRaises(requests.exceptions.ReadTimeout):
				response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
			with self.assertRaises(requests.exceptions.ConnectionError):
				response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
	def should_raise_on_http_errors(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
		mock_session = MockRequestSession(MockRequestSession.Response(
			status_code=404,
			content={'data':'test'},
			))
		real_response = requests.Response
		real_response.status_code = 404
		mock_session.raises(
				requests.exceptions.HTTPError(response=real_response),
				)
		with unittest.mock.patch('requests.Session', mock_session):
			with self.assertRaises(requests.exceptions.HTTPError):
				response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
	def should_retry_on_appserver_http_errors(self):
		obj = MockAPI('http://localhost/', 'login', 'password')
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
		with unittest.mock.patch('requests.Session', mock_session):
			with self.assertRaises(requests.exceptions.HTTPError):
				response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})

			response = obj.post('path', 'to', 'request', query1='param1', query2='param2', _body={'request':'value'})
			self.assertEqual(response, {'data':'test'})
