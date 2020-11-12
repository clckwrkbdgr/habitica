import unittest
unittest.defaultTestLoader.testMethodPrefix = 'should'
import requests
from .. import api

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
