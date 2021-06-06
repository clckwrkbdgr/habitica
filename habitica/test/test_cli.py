import unittest
unittest.defaultTestLoader.testMethodPrefix = 'should'
import textwrap
import datetime
import itertools
import io, contextlib
from .. import cli, core

class TestTaskFilter(unittest.TestCase):
	def _parse_args(self, args):
		return list(itertools.chain.from_iterable(map(cli.parse_task_number_arg, args)))
	def should_parse_task_number_argument(self):
		self.assertEqual(cli.parse_task_number_arg('1'), [0])
		self.assertEqual(cli.parse_task_number_arg('1.1'), [(0, 0)])
		self.assertEqual(cli.parse_task_number_arg('1-3'), [0, 1, 2])
		self.assertEqual(cli.parse_task_number_arg('1-3,5'), [0, 1, 2, 4])
		self.assertEqual(cli.parse_task_number_arg('1,3,5'), [0, 2, 4])
	def should_sort_task_ids(self):
		tids = self._parse_args(['1.2', '1', '2.1', '1.1', '3', '2.2'])
		actual = sorted(tids, key=cli.task_id_key)
		expected = self._parse_args(['1.1', '1.2', '1', '2.1', '2.2', '3'])
		self.assertEqual(actual, expected)
	def should_filter_tasks_by_patterns(self):
		todos = [
				core.Todo(_data={
					'text':'Wake up and yawn',
					'checklist' : [
						{'text':'wake up'},
						{'text':'yawn'},
						],
					}),
				core.Todo(_data={
					'text':'Complete all tasks',
					'checklist' : [
						{'text':'cross this item'},
						{'text':'complete all tasks'},
						{'text':'rest'},
						],
					}),
				]
		self.assertEqual([item.text for item in cli.filter_tasks(todos,
			['1', '1.1', 'complete', 'rest', 'Complete'],
			)], [
				'wake up',
				'Wake up and yawn',
				'complete all tasks',
				'rest',
				'Complete all tasks',
				])
		with self.assertRaises(RuntimeError) as e:
			list(cli.filter_tasks(todos, ['this', 'item']))
		with self.assertRaises(RuntimeError) as e:
			list(cli.filter_tasks(todos, ['Unknown']))
		with self.assertRaises(RuntimeError) as e:
			list(cli.filter_tasks(todos, ['all tasks']))

class TestPrinter(unittest.TestCase):
	def _get_tasks(self):
		return [
				core.Habit(_data={
					'text':'Keep Calm',
					'notes': 'and Carry On',
					}),
				core.Daily(_data={
					'text':'Wake up and yawn',
					'notes': 'This is the only daily for today',
					'frequency' : 'daily',
					'startDate' : '2020-02-20T10:10:10.000Z',
					'everyX' : 2,
					'completed' : False,
					'checklist' : [
						{'text':'wake up', 'completed':True},
						{'text':'yawn', 'completed':False},
						],
					}),
				core.Todo(_data={
					'text':'Complete all tasks',
					'notes': 'New Year Resolution',
					'completed' : True,
					'checklist' : [
						{'text':'cross this item', 'completed':False},
						{'text':'complete all tasks', 'completed':True},
						{'text':'rest', 'completed':False},
						],
					}),
				]
	def should_print_task_list(self):
		tasks = self._get_tasks()
		def _printer(line):
			_printer.output += line + '\n'
		_printer.output = ''
		cli.print_task_list(tasks, hide_completed=False, timezoneOffset=0, with_notes=False, time_now=datetime.datetime(2020, 2, 22, 0, 0, 1), printer=_printer)
		self.assertEqual(_printer.output, textwrap.dedent("""\
				1 Keep Calm
				[_] 2 Wake up and yawn
				    [X] 2.1 wake up
				    [_] 2.2 yawn
				[X] 3 Complete all tasks
				    [_] 3.1 cross this item
				    [X] 3.2 complete all tasks
				    [_] 3.3 rest
				"""))
	def should_print_notes(self):
		tasks = self._get_tasks()
		def _printer(line):
			_printer.output += line + '\n'
		_printer.output = ''
		cli.print_task_list(tasks, hide_completed=False, timezoneOffset=0, with_notes=True, time_now=datetime.datetime(2020, 2, 22, 0, 0, 1), printer=_printer)
		self.assertEqual(_printer.output, textwrap.dedent("""\
				1 Keep Calm
				      and Carry On
				[_] 2 Wake up and yawn
				      This is the only daily for today
				    [X] 2.1 wake up
				    [_] 2.2 yawn
				[X] 3 Complete all tasks
				      New Year Resolution
				    [_] 3.1 cross this item
				    [X] 3.2 complete all tasks
				    [_] 3.3 rest
				"""))
	def should_hide_completed_tasks(self):
		tasks = self._get_tasks()
		def _printer(line):
			_printer.output += line + '\n'
		_printer.output = ''
		cli.print_task_list(tasks, hide_completed=True, timezoneOffset=0, with_notes=False, time_now=datetime.datetime(2020, 2, 22, 0, 0, 1), printer=_printer)
		self.assertEqual(_printer.output, textwrap.dedent("""\
				1 Keep Calm
				[_] 2 Wake up and yawn
				    [X] 2.1 wake up
				    [_] 2.2 yawn
				"""))
	def should_hide_wront_time_dailies(self):
		tasks = self._get_tasks()
		def _printer(line):
			_printer.output += line + '\n'
		_printer.output = ''
		cli.print_task_list(tasks, hide_completed=False, timezoneOffset=0, with_notes=True, time_now=datetime.datetime(2020, 2, 21, 0, 0, 1), printer=_printer)
		self.assertEqual(_printer.output, textwrap.dedent("""\
				1 Keep Calm
				      and Carry On
				[X] 3 Complete all tasks
				      New Year Resolution
				    [_] 3.1 cross this item
				    [X] 3.2 complete all tasks
				    [_] 3.3 rest
				"""))
