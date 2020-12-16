""" Tasks: habits, dailies, todos.
Also rewards.
"""
from bisect import bisect
from .. import timeutils
from . import base

# Weekday abbreviations used in task frequencies.
HABITICA_WEEK = ["m", "t", "w", "th", "f", "s", "su"]

class Task(base.ApiObject):
	""" Parent class for any task (habit, daily, todo, reward). """
	DARK_RED, RED, ORANGE = -20, -10, -1
	YELLOW = 0
	GREEN, LIGHT_BLUE, BRIGHT_BLUE = 1, 5, 10

	@property
	def id(self):
		return self._data['id']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data.get('notes', '')

class Reward(Task):
	def _buy(self, user):
		self.api.post('tasks', self.id, 'score', 'up')

class TaskValue:
	""" Base trait for tasks that have value and colors (habit, daily, todo).
	Expects property .value
	"""
	@property
	def value(self):
		return self._data['value']
	@property
	def color(self):
		""" Returns virtual Task Color (see Task). """
		scores = [self.DARK_RED, self.RED, self.ORANGE, self.YELLOW, self.GREEN, self.LIGHT_BLUE, self.BRIGHT_BLUE]
		breakpoints = [-20, -10, -1, 1, 5, 10]
		return scores[bisect(breakpoints, self.value)]

class CannotScoreUp(Exception):
	def __init__(self, habit):
		self.habit = habit
	def __str__(self):
		return "Habit '{0}' cannot be incremented".format(self.habit.text)

class CannotScoreDown(Exception):
	def __init__(self, habit):
		self.habit = habit
	def __str__(self):
		return "Habit '{0}' cannot be decremented".format(self.habit.text)

class Habit(Task, TaskValue):
	@property
	def can_score_up(self):
		return self._data['up']
	@property
	def can_score_down(self):
		return self._data['down']
	def up(self):
		if not self._data['up']:
			raise CannotScoreUp(self)
		result = self.api.post('tasks', self.id, 'score', 'up').data
		self._data['value'] += result['delta']
	def down(self):
		if not self._data['down']:
			raise CannotScoreDown(self)
		result = self.api.post('tasks', self.id, 'score', 'down').data
		self._data['value'] += result['delta']

class Checkable:
	""" Base class for task or sub-item that can be checked (completed) or unchecked.
	"""
	@property
	def is_completed(self):
		return self._data['completed']
	def complete(self): # pragma: no cover
		""" Marks entry as completed. """
		self._data['completed'] = True
	def undo(self): # pragma: no cover
		""" Marks entry as not completed. """
		self._data['completed'] = False

class SubItem(Task, Checkable):
	@property
	def parent(self):
		return self._parent
	def complete(self):
		""" Marks subitem as completed. """
		if self.is_completed:
			return
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		super().complete()
	def undo(self):
		""" Marks subitem as not completed. """
		if not self.is_completed:
			return
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		super().undo()

class Checklist:
	""" Base class for task that provides list of checkable sub-items. """
	@property
	def checklist(self):
		""" Returns list of task's subitems.
		You can also get subitem directly from task:
		>>> task.checklist[item_id]
		>>> task[item_id]
		"""
		return self.children(SubItem, self._data['checklist'])
	def __getitem__(self, key):
		""" Returns SubItem object for given item index. """
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return self.child(SubItem, self._data['checklist'][key])

class Daily(Task, TaskValue, Checkable, Checklist):
	def is_due(self, today, timezoneOffset=None):
		""" Should return True is task is available for given day
		considering its repeat pattern and start date.
		"""
		if self._data['frequency'] == 'daily':
			if timeutils.days_passed(self._data['startDate'], today, timezoneOffset=timezoneOffset) % self._data['everyX'] != 0:
				return False
		elif self._data['frequency'] == 'weekly':
			if not self._data['repeat'][HABITICA_WEEK[today.weekday()]]:
				return False
		else: # pragma: no cover
			raise ValueError("Unknown daily frequency: {0}".format(self._data['frequency']))
		return True

	def complete(self):
		""" Marks daily as completed. """
		self.api.post('tasks', self.id, 'score', 'up')
		super().complete()
	def undo(self):
		""" Marks daily as not completed. """
		self.api.post('tasks', self.id, 'score', 'down')
		super().undo()

class Todo(Task, TaskValue, Checkable, Checklist):
	def complete(self):
		""" Marks todo as completed. """
		self.api.post('tasks', self.id, 'score', 'up')
		super().complete()
	def undo(self):
		""" Marks todo as not completed. """
		self.api.post('tasks', self.id, 'score', 'down')
		super().undo()
