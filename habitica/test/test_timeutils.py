import unittest
unittest.defaultTestLoader.testMethodPrefix = 'should'
from ..timeutils import days_passed, parse_isodate

class TestAutoRegistry(unittest.TestCase):
	def should_calculated_days_passed_between_task_start_and_now(self):
		self.assertEqual(
				days_passed('2016-06-20T21:00:00.000Z',
					parse_isodate('2016-11-08 16:51:15.930842'),
					timezoneOffset=-120
					),
				141
				)
		self.assertEqual(
				days_passed('2016-06-20T21:00:00.000Z',
					parse_isodate('2016-11-08 20:51:15.930842'),
					timezoneOffset=-120
					),
				141
				)
		self.assertEqual(
				days_passed('2016-06-20T21:00:00.000Z',
					parse_isodate('2016-11-08 21:51:15.930842'),
					timezoneOffset=-120
					),
				141
				)
		self.assertEqual(
				days_passed('2016-06-20T21:00:00.000Z',
					parse_isodate('2016-11-09 16:51:15.930842'),
					timezoneOffset=-120
					),
				142
				)
		self.assertEqual(
				days_passed('2015-07-01T16:50:07.000Z',
					parse_isodate('2016-10-23 16:51:15.930842'),
					timezoneOffset=-120
					),
				480
				)
		self.assertEqual(
				days_passed('2015-07-01T16:50:07.000Z',
					parse_isodate('2016-10-23 15:51:15.930842'),
					timezoneOffset=-120
					),
				480
				)
		self.assertEqual(
				days_passed('2015-07-01T16:50:07.000Z',
					parse_isodate('2016-10-23 21:51:15.930842'),
					timezoneOffset=-120
					),
				480
				)
		self.assertEqual(
				days_passed('2016-01-01T20:39:15.833Z',
					parse_isodate('2016-11-06 21:51:15.930842'),
					timezoneOffset=-120
					),
				310
				)
		self.assertEqual(
				days_passed('2016-01-01T20:39:15.833Z',
					parse_isodate('2016-11-06 20:31:15.930842'),
					timezoneOffset=-120
					),
				310
				)
		self.assertEqual(
				days_passed('2016-01-01T20:39:15.833Z',
					parse_isodate('2016-11-06 15:31:15.930842'),
					timezoneOffset=-120
					),
				310
				)
		self.assertEqual(
				days_passed('2016-12-30T22:00:00.000Z',
					parse_isodate('2017-01-03 19:46:59.290457'),
					timezoneOffset=-120
					),
				3
				)
