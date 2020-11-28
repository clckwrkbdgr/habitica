import unittest
unittest.defaultTestLoader.testMethodPrefix = 'should'
import itertools
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
	def should_find_task_in_list_by_pattern(self):
		tasks = [
				core.Habit(_data={'text':'Behave well'}),
				core.Daily(_data={
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
		self.assertEqual(cli.find_task_in_list('Behave', tasks), 0)
		self.assertEqual(cli.find_task_in_list('wake up', tasks), (1,0))
		with self.assertRaises(RuntimeError) as e:
			cli.find_task_in_list('Unknown', tasks)
		with self.assertRaises(RuntimeError) as e:
			cli.find_task_in_list('all tasks', tasks)
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
