""" Tasks: habits, dailies, todos.
Also rewards.
"""
from bisect import bisect
from .. import timeutils
from . import base, tags

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

class Reminder(base.Entity): # pragma: no cover -- TODO no way to create yet.
	@property
	def startDate(self):
		return self._data['startDate']
	@property
	def time(self):
		return self._data['time']

class Task(base.Entity):
	""" Parent class for any task (habit, daily, todo, reward). """
	DARK_RED, RED, ORANGE = -20, -10, -1
	YELLOW = 0
	GREEN, LIGHT_BLUE, BRIGHT_BLUE = 1, 5, 10

	class Priority:
		TRIVIAL = 0.1
		EASY = 1
		MEDIUM = 1.5
		HARD = 2.0

	# TODO GET /tasks/:id
	def __init__(self, text=None,
			alias=None,
			attribute=None,
			collapseChecklist=None,
			notes=None,
			priority=None,
			reminders=None,
			tags=None,
			# API args:
			**kwargs
			):
		if text is None:
			super().__init__(**kwargs)
			return
		self._data = {
				'text' : text,
				'type' : self.task_type,
				}
		if alias is not None:
			self._data['alias'] = alias
		if attribute is not None:
			self._data['attribute'] = attribute
		if collapseChecklist is not None:
			self._data['collapseChecklist'] = collapseChecklist
		if notes is not None:
			self._data['notes'] = notes
		if priority is not None:
			self._data['priority'] = priority
		if reminders is not None:
			self._data['reminders'] = reminders
		if tags is not None:
			self._data['tags'] = tags
	def update(self, text=None,
			attribute=None,
			collapseChecklist=None,
			notes=None,
			priority=None,
			reminders=None,
			tags=None,
			**specific_args
			):
		_body = specific_args
		if text is not None:
			_body['text'] = text
		if attribute is not None:
			_body['attribute'] = attribute
		if collapseChecklist is not None:
			_body['collapseChecklist'] = collapseChecklist
		if notes is not None:
			_body['notes'] = notes
		if priority is not None:
			_body['priority'] = priority
		if reminders is not None:
			_body['reminders'] = reminders
		if tags is not None:
			_body['tags'] = tags
		self._data = self.api.put('tasks', self.id, _body=_body).data

	@property
	def task_type(self):
		""" Returns string value of task type. """
		allowed_task_types = {
				Reward : 'reward',
				Habit : 'habit',
				Daily : 'daily',
				Todo : 'todo',
				}
		return allowed_task_types[type(self)]
	@staticmethod
	def type_from_str(strtype):
		""" Returns task type by its string value. """
		allowed_task_types = {
				'reward' : Reward,
				'habit' : Habit,
				'daily' : Daily,
				'todo' : Todo,
				}
		return allowed_task_types[strtype]
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
		return self.children(tags.Tag, self._data['tags'])
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
	def add_tag(self, tag):
		self._data = self.api.post('tasks', self.id, 'tags', tag.id).data
	def delete_tag(self, tag):
		self._data = self.api.delete('tasks', self.id, 'tags', tag.id).data
	def approve_for(self, member):
		self._data = self.api.post('tasks', self.id, 'approve', member.id).data
	def assign_to(self, member):
		self._data = self.api.post('tasks', self.id, 'assign', member.id).data
	def unassign_from(self, member):
		self._data = self.api.post('tasks', self.id, 'unassign', member.id).data
	def delete_task(self):
		""" Deletes task from server and resets internal data of this object. """
		self._data = self.api.delete('tasks', self.id).data
	def move_to(self, new_pos):
		""" Move task to a new position in corresponding list.
		0 is the top, -1 is the bottom.
		Returns list of Task IDs in new order.
		"""
		return self.api.post('tasks', self.id, 'move', 'to', str(new_pos)).data
	def needs_work(self, assigned_user):
		self.data = self.api.post('tasks', self.id, 'needs-work', assigned_user.id).data
	def unlink_from_challenge(self, keep=False):
		self.api.post('tasks', 'unlink-one', self.id, keep='keep' if keep else 'remove')

class Reward(Task, base.MarketableForGold):
	def __init__(self, text=None, alias=None, attribute=None, collapseChecklist=None,
			notes=None, priority=None, reminders=None, tags=None,
			# Reward-only fields:
			value=None,
			# API args:
			**kwargs
			):
		super().__init__(
				text=text,
				alias=alias,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**kwargs,
				)
		if text is not None:
			if value is not None:
				self._data['value'] = value
	def update(self, text=None,
			notes=None,
			tags=None,
			# Reward-specific args:
			value=None,
			):
		specific_args = {}
		if value is not None:
			specific_args['value'] = value
		super().update(
				text=text,
				notes=notes,
				tags=tags,
				**specific_args
				)
	@property
	def value(self):
		return base.Price(self._data['value'], 'gold')
	def _buy(self, user):
		# TODO data also stores updated user stats, needs to calculate diff and notify.
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
	def __init__(self, text=None, alias=None, attribute=None, collapseChecklist=None,
			notes=None, priority=None, reminders=None, tags=None,
			# Habit-only fields:
			up=None,
			down=None,
			# API args:
			**kwargs
			):
		super().__init__(
				text=text,
				alias=alias,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**kwargs,
				)
		if text is not None:
			if up is not None:
				self._data['up'] = up
			if down is not None:
				self._data['down'] = down
	def update(self, text=None,
			attribute=None,
			collapseChecklist=None,
			notes=None,
			priority=None,
			reminders=None,
			tags=None,
			# Habit-specific args:
			up=None,
			down=None,
			):
		specific_args = {}
		if up is not None:
			specific_args['up'] = up
		if down is not None:
			specific_args['down'] = down
		super().update(
				text=text,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**specific_args
				)
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
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		result = self.api.post('tasks', self.id, 'score', 'up').data
		self._data['value'] += result['delta']
	def down(self):
		if not self._data['down']:
			raise CannotScoreDown(self)
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
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
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		super().complete()
	def undo(self):
		""" Marks subitem as not completed. """
		if not self.is_completed:
			return
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		super().undo()
	def update(self, text):
		self._parent._data = self.api.put('tasks', self._parent.id, 'checklist', self.id, _body={'text':text}).data

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
	def append(self, text):
		self._data = self.api.post('tasks', self.id, 'checklist', _body={
			'text' : text,
			}).data
	def delete(self, item):
		self._data = self.api.delete('tasks', self.id, 'checklist', item.id).data

class DailyFrequency(base.ApiObject):
	def __init__(self,
			startDate=None,
			everyX=None,
			# API args:
			**kwargs
			):
		self._data = {}
		if startDate is not None:
			self._data['startDate'] = startDate
		if everyX is not None:
			self._data['everyX'] = everyX
		if not self._data:
			super().__init__(**kwargs)
			return
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

class WeeklyFrequency(base.ApiObject):
	# Weekday abbreviations used in task frequencies.
	ABBR = ["m", "t", "w", "th", "f", "s", "su"]

	def __init__(self,
			monday=None,
			tuesday=None,
			wednesday=None,
			thursday=None,
			friday=None,
			saturday=None,
			sunday=None,
			# API args:
			**kwargs
			):
		values = [
			monday, tuesday, wednesday, thursday, friday, saturday, sunday,
			]
		repeat = {}
		for name, value in zip(self.ABBR, values):
			if value is not None:
				repeat[name] = bool(value)
		if not repeat:
			super().__init__(**kwargs)
			return
		self._data = {'repeat': repeat}
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
	class Frequency:
		DAILY = 'daily'
		WEEKLY = 'weekly'
		MONTHLY = 'monthly'
		YEARLY = 'yearly'

	# TODO history
	def __init__(self, text=None, alias=None, attribute=None, collapseChecklist=None,
			notes=None, priority=None, reminders=None, tags=None,
			# Todo-only fields:
			frequency=None, # DailyFrequency or WeeklyFrequency
			streak=None,
			# API args:
			**kwargs
			):
		super().__init__(
				text=text,
				alias=alias,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**kwargs,
				)
		if text is not None:
			if frequency is not None:
				assert type(frequency) in (DailyFrequency, WeeklyFrequency)
				frequency_type = {
						DailyFrequency : self.Frequency.DAILY,
						WeeklyFrequency : self.Frequency.WEEKLY,
						}
				self._data['frequency'] = frequency_type[type(frequency)]
				if self._data['frequency'] == self.Frequency.WEEKLY:
					self._data.update(frequency._data)
				elif self._data['frequency'] == self.Frequency.DAILY:
					self._data.update(frequency._data)
				else: # pragma: no cover
					# TODO daysOfMonth for Daily (monthly?)
					# TODO weeksOfMonth for Daily (monthly?)
					raise RuntimeError('Frequencies other than daily or weekly are not supported (yet).')
			if streak is not None:
				self._data['streak'] = streak
	def update(self, text=None,
			attribute=None,
			collapseChecklist=None,
			notes=None,
			priority=None,
			reminders=None,
			tags=None,
			# Daily-specific args:
			frequency=None,
			# TODO frequency, repeat, everyX, streak, daysOfMonth, weeksOfMonth, startDate (daily)
			streak=None,
			):
		specific_args = {}
		if frequency is not None:
			assert type(frequency) in (DailyFrequency, WeeklyFrequency)
			frequency_type = {
					DailyFrequency : self.Frequency.DAILY,
					WeeklyFrequency : self.Frequency.WEEKLY,
					}[type(frequency)]
			if self._data['frequency'] != frequency_type:
				specific_args['frequency'] = frequency_type
			if frequency_type == self.Frequency.WEEKLY:
				specific_args['repeat'] = frequency._data['repeat']
			elif frequency_type == self.Frequency.DAILY:
				if self._data['frequency'] != frequency_type:
					specific_args.update(frequency._data)
				else:
					if 'everyX' in frequency._data and self._data['everyX'] != frequency._data['everyX']:
						specific_args['everyX'] = frequency._data['everyX']
					if 'startDate' in frequency._data and self._data['startDate'] != frequency._data['startDate']:
						specific_args['startDate'] = frequency._data['startDate']
			else: # pragma: no cover
				# TODO daysOfMonth for Daily (monthly?)
				# TODO weeksOfMonth for Daily (monthly?)
				raise RuntimeError('Frequencies other than daily or weekly are not supported (yet).')
		if streak is not None:
			specific_args['streak'] = streak
		super().update(
				text=text,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**specific_args
				)
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
		if self.frequency == Daily.Frequency.DAILY:
			return self.child(DailyFrequency, self._data)
		elif self.frequency == Daily.Frequency.WEEKLY:
			return self.child(WeeklyFrequency, self._data)
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
		if self._data['frequency'] == Daily.Frequency.DAILY:
			if timeutils.days_passed(self._data['startDate'], today, timezoneOffset=timezoneOffset) % self._data['everyX'] != 0:
				return False
		elif self._data['frequency'] == Daily.Frequency.WEEKLY:
			if not self._data['repeat'][WeeklyFrequency.ABBR[today.weekday()]]:
				return False
		else: # pragma: no cover
			raise ValueError("Unknown daily frequency: {0}".format(self._data['frequency']))
		return True

	def complete(self):
		""" Marks daily as completed. """
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		result = self.api.post('tasks', self.id, 'score', 'up').data
		self._data['value'] += result['delta']
		super().complete()
	def undo(self):
		""" Marks daily as not completed. """
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		result = self.api.post('tasks', self.id, 'score', 'down').data
		self._data['value'] += result['delta']
		super().undo()

class Todo(Task, TaskValue, Checkable, Checklist):
	def __init__(self, text=None, alias=None, attribute=None, collapseChecklist=None,
			notes=None, priority=None, reminders=None, tags=None,
			# Todo-only fields:
			date=None,
			# API args:
			**kwargs
			):
		super().__init__(
				text=text,
				alias=alias,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**kwargs,
				)
		if text is not None:
			if date is not None:
				self._data['date'] = date.strftime('%Y-%m-%d')
	def update(self, text=None,
			attribute=None,
			collapseChecklist=None,
			notes=None,
			priority=None,
			reminders=None,
			tags=None,
			# Todo-specific args:
			date=None,
			):
		specific_args = {}
		if date is not None:
			specific_args['date'] = date
		super().update(
				text=text,
				attribute=attribute,
				collapseChecklist=collapseChecklist,
				notes=notes,
				priority=priority,
				reminders=reminders,
				tags=tags,
				**specific_args
				)
	@property
	def date(self):
		return self._data['date']
	@property
	def dateCompleted(self):
		return self._data['dateCompleted'] # FIXME parse date
	def complete(self):
		""" Marks todo as completed. """
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		result = self.api.post('tasks', self.id, 'score', 'up').data
		self._data['value'] += result['delta']
		super().complete()
	def undo(self):
		""" Marks todo as not completed. """
		# TODO data also stores updated user stats, needs to calculate diff and notify.
		# TODO also data._tmp is a Drop, need to display notification.
		result = self.api.post('tasks', self.id, 'score', 'down').data
		self._data['value'] += result['delta']
		super().undo()
