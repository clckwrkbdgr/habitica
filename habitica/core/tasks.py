""" Tasks: habits, dailies, todos.
Also rewards.
"""
from bisect import bisect
from .. import timeutils
from . import base

class Approval(base.ApiObject):
	@property
	def required(self):
		return self._data['required']
	@property
	def dateApproved(self):
		return self._data['dateApproved'] # FIXME parse date
	@property
	def approvingUser(self):
		return self._data['approvingUser']
	@property
	def requested(self):
		return self._data['requested']
	@property
	def requestedDate(self):
		return self._data['requestedDate']

class GroupInfo(base.Entity):
	def __call__(self):
		from . import groups
		return self.child(groups.Group, self.api.get('groups', self.id).data)
	@property
	def broken(self):
		return self._data['broken']
	@property
	def assignedUsers(self):
		return self._data['assignedUsers'] # Array. FIXME of Members?
	@property
	def assignedDate(self):
		return self._data['assignedDate'] # FIXME parse date
	@property
	def assignedUsername(self):
		return self._data['assignedUsername']
	@property
	def taskId(self):
		return self._data['taskId']
	@property
	def sharedCompletion(self):
		return self._data['sharedCompletion']
	@property
	def managerNotes(self):
		return self._data['managerNotes']
	@property
	def approval(self):
		return self.child(Approval, self._data['approval'])

class ChallengeInfo(base.Entity):
	def __call__(self):
		from . import groups
		return self.child(groups.Challenge, self.api.get('challenges', self.id).data)
	@property
	def shortName(self):
		return self._data['shortName']
	@property
	def taskId(self):
		return self._data['taskId']
	@property
	def broken(self):
		return self._data['broken']
	@property
	def winner(self):
		return self._data['winner']

class Task(base.Entity):
	""" Parent class for any task (habit, daily, todo, reward). """
	DARK_RED, RED, ORANGE = -20, -10, -1
	YELLOW = 0
	GREEN, LIGHT_BLUE, BRIGHT_BLUE = 1, 5, 10

	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data.get('notes', '')
	@property
	def type(self):
		return self._data['type']
	@property
	def createdAt(self):
		return self._data['createdAt'] # FIXME parse date
	@property
	def updatedAt(self):
		return self._data['updatedAt'] # FIXME parse date
	@property
	def byHabitica(self):
		return self._data['byHabitica']
	@property
	def alias(self):
		return self._data['alias']
	@property
	def tags(self): # pragma: no cover -- FIXME produce Tag children.
		return self._data['tags']
	@property
	def priority(self):
		return self._data['priority']
	@property
	def attribute(self):
		return self._data['attribute'] # TODO is it one of base stats?
	@property
	def userId(self):
		return self._data['userId']
	@property
	def reminders(self):
		return self._data['reminders'] # TODO
	@property
	def group(self):
		return self.child(GroupInfo, self._data['group'])
	@property
	def challenge(self):
		return self.child(ChallengeInfo, self._data['challenge'])

class Reward(Task):
	@property
	def value(self):
		return base.Price(self._data['value'], 'gold')
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
	# TODO history
	@property
	def can_score_up(self):
		return self._data['up']
	@property
	def can_score_down(self):
		return self._data['down']
	@property
	def counterUp(self):
		return self._data['counterUp']
	@property
	def counterDown(self):
		return self._data['counterDown']
	@property
	def frequency(self):
		return self._data['frequency']
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
	def collapseChecklist(self):
		return self._data['collapseChecklist']
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

class DailyTrigger(base.ApiObject):
	@property
	def startDate(self):
		return self._data['startDate']
	@property
	def everyX(self):
		return self._data['everyX']
	@property
	def daysOfMonth(self):
		return self._data['daysOfMonth']
	@property
	def weeksOfMonth(self):
		return self._data['weeksOfMonth']

class WeeklyTrigger(base.ApiObject):
	# Weekday abbreviations used in task frequencies.
	ABBR = ["m", "t", "w", "th", "f", "s", "su"]

	@property
	def weekdays(self):
		""" Returns list of weekday numbers (starts with Mon=0). """
		return [weekday for weekday in range(7) if self._data['repeat'][self.ABBR[weekday]]]
	@property
	def monday(self):
		return self._data['repeat'][self.ABBR[0]]
	@property
	def tuesday(self):
		return self._data['repeat'][self.ABBR[1]]
	@property
	def wednesday(self):
		return self._data['repeat'][self.ABBR[2]]
	@property
	def thursday(self):
		return self._data['repeat'][self.ABBR[3]]
	@property
	def friday(self):
		return self._data['repeat'][self.ABBR[4]]
	@property
	def saturday(self):
		return self._data['repeat'][self.ABBR[5]]
	@property
	def sunday(self):
		return self._data['repeat'][self.ABBR[6]]

class Daily(Task, TaskValue, Checkable, Checklist):
	# TODO history
	@property
	def streak(self):
		return self._data['streak']
	@property
	def yesterDaily(self):
		return self._data['yesterDaily']
	@property
	def frequency(self):
		return self._data['frequency']
	@property
	def trigger(self):
		if self.frequency == 'daily':
			return self.child(DailyTrigger, self._data)
		elif self.frequency == 'weekly':
			return self.child(WeeklyTrigger, self._data)
		else: # pragma: no cover
			raise ValueError("Unknown daily frequency: {0}".format(self._data['frequency']))
	@property
	def isDue(self): # TODO ??? is it really == is_due(today) ?
		return self._data['isDue']
	@property
	def nextDue(self):
		return self._data['nextDue'] # TODO Array. probably of dates.
	def is_due(self, today, timezoneOffset=None):
		""" Should return True is task is available for given day
		considering its repeat pattern and start date.
		"""
		if self._data['frequency'] == 'daily':
			if timeutils.days_passed(self._data['startDate'], today, timezoneOffset=timezoneOffset) % self._data['everyX'] != 0:
				return False
		elif self._data['frequency'] == 'weekly':
			if not self._data['repeat'][WeeklyTrigger.ABBR[today.weekday()]]:
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
	@property
	def date(self):
		return self._data['date']
	@property
	def dateCompleted(self):
		return self._data['dateCompleted'] # FIXME parse date
	def complete(self):
		""" Marks todo as completed. """
		self.api.post('tasks', self.id, 'score', 'up')
		super().complete()
	def undo(self):
		""" Marks todo as not completed. """
		self.api.post('tasks', self.id, 'score', 'down')
		super().undo()
