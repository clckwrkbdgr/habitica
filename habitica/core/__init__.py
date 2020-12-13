import os
import json
import datetime, time
import logging
from bisect import bisect
from pathlib import Path
from functools import lru_cache
from collections import namedtuple
from .. import api, config
from .. import timeutils

HabiticaEvent = namedtuple('HabiticaEvent', 'start end')

# Weekday abbreviations used in task frequencies.
HABITICA_WEEK = ["m", "t", "w", "th", "f", "s", "su"]

class Content:
	""" Cache for all Habitica content. """
	def __init__(self, _api=None):
		self.api = _api
		self._data = self.api.cached('content').get('content').data
	@property
	def potion(self):
		return HealthPotion(_api=self.api, _data=self._data['potion'])
	@property
	def armoire(self):
		return Armoire(_api=self.api, _data=self._data['armoire'])
	@property
	def classes(self):
		return self._data['classes']
	@property
	def gearTypes(self):
		return self._data['gearTypes']
	def questEggs(self):
		return [Egg(_api=self.api, _data=entry) for entry in self._data['questEggs'].values()]
	def eggs(self):
		return [Egg(_api=self.api, _data=entry) for entry in self._data['eggs'].values()]
	def dropEggs(self):
		return [Egg(_api=self.api, _data=entry) for entry in self._data['dropEggs'].values()]
	def wackyHatchingPotions(self):
		return [HatchingPotion(_api=self.api, _data=entry) for entry in self._data['wackyHatchingPotions'].values()]
	def hatchingPotions(self):
		return [HatchingPotion(_api=self.api, _data=entry) for entry in self._data['hatchingPotions'].values()]
	def dropHatchingPotions(self):
		return [HatchingPotion(_api=self.api, _data=entry) for entry in self._data['dropHatchingPotions'].values()]
	def premiumHatchingPotions(self):
		return [HatchingPotion(_api=self.api, _data=entry) for entry in self._data['premiumHatchingPotions'].values()]
	def petInfo(self, key=None):
		if key:
			return Pet(_api=self.api, _data=self._data['petInfo'][key])
		return [Pet(_api=self.api, _data=entry) for entry in self._data['petInfo'].values()]
	def questPets(self):
		return [Pet(_api=self.api, _data=self._data['petInfo'][key]) for key, value in self._data['questPets'].items() if value]
	def premiumPets(self):
		return [Pet(_api=self.api, _data=self._data['petInfo'][key]) for key, value in self._data['premiumPets'].items() if value]
	def specialPets(self):
		return [Pet(_api=self.api, _data=self._data['petInfo'][key], _special=value) for key, value in self._data['specialPets'].items() if value]
	def mountInfo(self, key=None):
		if key:
			return Mount(_api=self.api, _data=self._data['mountInfo'][key])
		return [Mount(_api=self.api, _data=entry) for entry in self._data['mountInfo'].values()]
	def mounts(self):
		return [Mount(_api=self.api, _data=self._data['mountInfo'][key]) for key, value in self._data['mounts'].items() if value]
	def questMounts(self):
		return [Mount(_api=self.api, _data=self._data['mountInfo'][key]) for key, value in self._data['questMounts'].items() if value]
	def premiumMounts(self):
		return [Mount(_api=self.api, _data=self._data['mountInfo'][key]) for key, value in self._data['premiumMounts'].items() if value]
	def specialMounts(self):
		return [Mount(_api=self.api, _data=self._data['mountInfo'][key], _special=value) for key, value in self._data['specialMounts'].items() if value]
	def get_background(self, name):
		return Background(_data=self._data['backgroundFlats'][name], _api=self.api)
	def get_background_set(self, year, month=None):
		""" Returns background set for given year and month.
		If month is None, returns all sets for this year.
		If year is None (explicitly), returns time travel backgrounds.
		"""
		if year is None: # TODO time travel - needs some constant name
			return [Background(_api=self.api, _data=entry) for entry in self._data['backgrounds']['timeTravelBackgrounds']]
		months = ['{0:02}'.format(month)] if month else ['{0:02}'.format(number) for number in range(1, 13)]
		patterns = ['backgrounds{month}{year}'.format(year=year, month=month) for month in months]
		result = []
		for key in self._data['backgrounds']:
			if key in patterns:
				result += [Background(_api=self.api, _data=entry) for entry in self._data['backgrounds'][key]]
		return result
	def __getitem__(self, key):
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return self._data[key]

class Armoire:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def text(self):
		return self._data['text']
	@property
	def key(self):
		return self._data['key']
	@property
	def type(self):
		return self._data['type']
	@property
	def cost(self):
		return self._data['value']
	@property
	def currency(self):
		return 'gold'

class Egg:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def key(self):
		return self._data['key']
	@property
	def text(self):
		return self._data['text']
	@property
	def mountText(self):
		return self._data['mountText']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def adjective(self):
		return self._data['adjective']
	@property
	def price(self):
		return self._data['value']
	@property
	def currency(self):
		return 'gems'

class HatchingPotion:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def key(self):
		return self._data['key']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def _addlNotes(self):
		return self._data.get('_addlNotes', '')
	@property
	def price(self):
		return self._data['value']
	@property
	def currency(self):
		return 'gems'
	@property
	def premium(self):
		return self._data.get('premium', False)
	@property
	def limited(self):
		return self._data.get('limited', False)
	@property
	def wacky(self):
		return self._data.get('wacky', False)
	@property
	def event(self):
		if 'event' not in self._data:
			return None
		start = datetime.datetime.strptime(self._data['event']['start'], '%Y-%m-%d').date()
		end = datetime.datetime.strptime(self._data['event']['end'], '%Y-%m-%d').date()
		return HabiticaEvent(start, end)

class Food: # pragma: no cover -- FIXME no methods to retrieve yet.
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def key(self):
		return self._data['key']
	@property
	def text(self):
		return self._data['text']
	@property
	def textThe(self):
		return self._data['textThe']
	@property
	def textA(self):
		return self._data['textA']
	@property
	def target(self):
		return self._data['target']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def canDrop(self):
		return self._data['canDrop']
	@property
	def price(self):
		return self._data['value']
	@property
	def currency(self):
		return 'gems'

class Background:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def key(self):
		return self._data['key']
	@property
	def price(self):
		return self._data['price']
	@property
	def currency(self):
		return self._data['currency'] if 'currency' in self._data else 'gems'
	@property
	def set_name(self):
		return self._data['set']

class Challenge:
	# TODO get challenge by id: get:/challenges/:id
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def name(self):
		return self._data['name']
	@property
	def shortName(self):
		return self._data['shortName']
	@property
	def summary(self):
		return self._data['summary']
	@property
	def updatedAt(self):
		return self._data['updatedAt'] # FIXME convert to date time using user TZ.
	@property
	def createdAt(self):
		return self._data['createdAt'] # FIXME convert to date time using user TZ.
	@property
	def prize(self):
		return self._data['prize']
	@property
	def memberCount(self):
		return self._data['memberCount']
	@property
	def official(self):
		return self._data['official']
	def rewards(self):
		return [Reward(_data=self.api.get('tasks', task_id).data, _api=self.api) for task_id in self._data['tasksOrder']['rewards']]
	def todos(self):
		return [Todo(_data=self.api.get('tasks', task_id).data, _api=self.api) for task_id in self._data['tasksOrder']['todos']]
	def dailies(self):
		return [Daily(_data=self.api.get('tasks', task_id).data, _api=self.api) for task_id in self._data['tasksOrder']['dailys']]
	def habits(self):
		return [Habit(_data=self.api.get('tasks', task_id).data, _api=self.api) for task_id in self._data['tasksOrder']['habits']]
	def leader(self):
		# FIXME get person profile by id.
		return self._data['leader']
	def group(self):
		# FIXME get group by id.
		return Group(_data=self._data['group'], _api=self.api)
	def as_csv(self):
		return self.api.get('challenges', self.id, 'export', 'csv')
	def clone(self):
		return Challenge(_api=self.api,
				_data=self.api.post('challenges', self.id, 'clone').challenge,
				)
	def update(self, name=None, summary=None, description=None):
		params = dict()
		if name:
			params['name'] = name
		if description:
			params['description'] = description
		if summary:
			params['summary'] = summary
		if not params:
			return
		self._data = self.api.put('challenges', self.id, _body=params).data
	def join(self):
		self._data = self.api.post('challenges', self.id, 'join').data
	def leave(self):
		self.api.post('challenges', self.id, 'leave')
	def selectWinner(self, person):
		self.api.post('challenges', self.id, 'selectWinner', person.id)
	def delete(self):
		self.api.delete('challenges', self.id)

class ChatMessage:
	def __init__(self, _data=None, _api=None, _group=None):
		self._data = _data
		self.api = _api
		self.group = _group
	@property
	def id(self):
		return self._data['id']
	@property
	def user(self):
		""" Name of the author of the message or 'system' for system messages. """
		return self._data['user'] if 'user' in self._data else 'system'
	@property
	def timestamp(self):
		""" Returns timestamp with msec. """
		return int(self._data['timestamp']) # TODO return datetime with user TZ
	# TODO likes:Object, flags:Object, flagCount:depends on flags?
	@property
	def text(self):
		return self._data['text']
	def flag(self, comment=None):
		params = dict()
		if comment:
			params['comment'] = comment
		self._data = self.api.post('groups', self.group.id, 'chat', self.id, 'flag', **params).data
	def like(self):
		self._data = self.api.post('groups', self.group.id, 'chat', self.id, 'like').data
	def clearflags(self):
		self.api.post('groups', self.group.id, 'chat', self.id, 'clearflags')

class Chat:
	def __init__(self, _api=None, _group=None):
		self.api = _api
		self._group = _group
		self._entries = None
	def __call__(self):
		return self.messages()
	def messages(self):
		if self._entries is None:
			self._entries = [ChatMessage(entry, _group=self._group, _api=self.api) for entry in self.api.get('groups', self._group.id, 'chat').data]
		return self._entries
	def mark_as_read(self):
		self.api.post('groups', self._group.id, 'chat', 'seen')
	def delete(self, message):
		if self._entries:
			new_entries = self.api.delete('groups', self._group.id, 'chat', message.id, previousMsg=self._entries[-1].id).data
			self._entries = [ChatMessage(entry, _group=self._group, _api=self.api) for entry in new_entries]
		else:
			self.api.delete('groups', self._group.id, 'chat', message.id)
	def post(self, message_text):
		if self._entries:
			new_entries = self.api.post('groups', self._group.id, 'chat', previousMsg=self._entries[-1].id,  _body={'message':message_text}).data
		else:
			new_entries = self.api.post('groups', self._group.id, 'chat', _body={'message':message_text}).data
		self._entries = [ChatMessage(entry, _group=self._group, _api=self.api) for entry in new_entries]

class Group:
	""" Habitica's user group: a guild, a party, the Tavern. """
	PARTY = 'party'
	GUILDS = 'guilds'
	PRIVATE_GUILDS = 'privateGuilds'
	PUBLIC_GUILDS = 'publicGuilds'
	TAVERN = 'tavern'

	PRIVATE, PUBLIC = 'private', 'public'

	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def name(self):
		return self._data['name']
	@property
	def type(self):
		return self._data['type']
	@property
	def privacy(self):
		return self._data['privacy']
	def challenges(self):
		return [Challenge(_data=entry, _api=self.api) for entry in self.api.get('challenges', 'groups', self.id).data]
	@property
	def chat(self):
		return Chat(_api=self.api, _group=self)
	def mark_chat_as_read(self):
		self.chat.mark_as_read()
	def create_challenge(self, name, shortName, summary=None, description=None, prize=0):
		""" Creates challenge with specified name and tag (shortName).
		Summary and description are optional.
		Prize is a number of gems (optional, default is 0).
		"""
		params = {
				'group' : self.id,
				'name' : name,
				'shortName' : shortName,
				}
		if summary:
			params['summary'] = summary[:250]
		if description:
			params['description'] = description
		if prize:
			params['prize'] = int(prize)
		# TODO body['official'] (for admins only, need roles).
		data = self.api.post('challenges', _body={
			'challenge' : params,
			}).data
		return Challenge(_api=self.api, _data=data)

class Quest:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@lru_cache()
	def _content(self):
		return Content(_api=self.api)['quests'][self.key] # TODO reuse Content object from Habitica.
	@property
	def active(self):
		return bool(self._data['active'])
	@property
	def key(self):
		return self._data['key']
	@property
	def title(self):
		return self._content()['text']
	@property
	def progress(self):
		if self._content().get('collect'):
			qp_tmp = self._data['progress']['collect']
			quest_progress = sum(qp_tmp.values())
			return quest_progress
		else:
			return self._data['progress']['hp']
	@property
	def max_progress(self):
		content = self._content()
		if content.get('collect'):
			return sum([int(item['count']) for item in content['collect'].values()])
		else:
			return content['boss']['hp']

class Party(Group):
	def __init__(self, _data=None, _api=None):
		super().__init__(_data=_data, _api=_api)
	@property
	def quest(self):
		return Quest(_data=self._data['quest'], _api=self.api)

class UserPreferences:
	def __init__(self, _data=None):
		self._data = _data
	@property
	def timezoneOffset(self):
		return self._data['timezoneOffset']

class UserStats:
	def __init__(self, _data=None):
		self._data = _data
	@property
	def class_name(self):
		return self._data['class']
	@property
	def hp(self):
		return self._data['hp']
	@property
	def maxHealth(self):
		return self._data['maxHealth']
	@property
	def level(self):
		return self._data['lvl']
	@property
	def experience(self):
		return self._data['exp']
	@property
	def maxExperience(self):
		return self._data['exp'] + self._data['toNextLevel']
	@property
	def mana(self):
		return self._data['mp']
	@property
	def maxMana(self):
		return self._data['maxMP']
	@property
	def gold(self):
		return self._data['gp']

class HealthOverflowError(Exception):
	def __init__(self, hp, maxHealth):
		self.hp, self.maxHealth = hp, maxHealth
	def __str__(self):
		return 'HP is too high, part of health potion would be wasted.'

class Item:
	def __init__(self, _data=None):
		self._data = _data

class HealthPotion:
	""" Health potion (+15 hp). """
	VALUE = 15.0
	def __init__(self, overflow_check=True, _api=None, _data=None):
		""" If overflow_check is True and there is less than 15 hp damage,
		so buying potion will result in hp bar overflow and wasting of potion,
		raises HealthOverflowError.
		"""
		self.api = _api
		self._data = _data
		self.overflow_check = overflow_check
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def key(self):
		return self._data['key']
	@property
	def type(self):
		return self._data['type']
	@property
	def cost(self):
		return self._data['value']
	@property
	def currency(self):
		return 'gold'
	def _buy(self, user):
		if self.api is None:
			self.api = user.api
		if self.overflow_check and user.stats.hp + self.VALUE > user.stats.maxHealth:
			raise HealthOverflowError(user.stats.hp, user.stats.maxHealth)
		user._data = self.api.post('user', 'buy-health-potion').data

class Pet:
	def __init__(self, _data=None, _api=None, _special=None):
		self.api = _api
		self._data = _data
		self._special = _special
	def __str__(self):
		return self.text
	@property
	def text(self):
		return self._data['text']
	@property
	def key(self):
		return self._data['key']
	@property
	def type(self):
		return self._data['type']
	@property
	def egg(self):
		return self._data.get('egg', None)
	@property
	def potion(self):
		return self._data.get('potion', None)
	@property
	def canFind(self):
		return self._data.get('canFind', None)
	@property
	def special(self):
		return self._special

class Mount:
	def __init__(self, _data=None, _api=None, _special=None):
		self.api = _api
		self._data = _data
		self._special = _special
	def __str__(self):
		return self.text
	@property
	def text(self):
		return self._data['text']
	@property
	def key(self):
		return self._data['key']
	@property
	def type(self):
		return self._data['type']
	@property
	def egg(self):
		return self._data.get('egg', None)
	@property
	def potion(self):
		return self._data.get('potion', None)
	@property
	def canFind(self):
		return self._data.get('canFind', None)
	@property
	def special(self):
		return self._special

class Inventory:
	def __init__(self, _data=None, _api=None, _content=None):
		self.api = _api
		self.content = _content
		self._data = _data
	@property
	def food(self):
		return [Item(_data=entry) for entry in self._data['food']]
	@property
	def pet(self):
		return self.content.petInfo(self._data['currentPet']) if self._data['currentPet'] else None
	@property
	def mount(self):
		return self.content.mountInfo(self._data['currentMount']) if self._data['currentMount'] else None

class Reward:
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def text(self):
		return self._data['text']
	def _buy(self, user):
		self.api.post('tasks', self.id, 'score', 'up')

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

class Task:
	""" Parent class for any task (habit, daily, todo). """
	DARK_RED, RED, ORANGE = -20, -10, -1
	YELLOW = 0
	GREEN, LIGHT_BLUE, BRIGHT_BLUE = 1, 5, 10

class Habit(Task):
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
	@property
	def value(self):
		return self._data['value']
	@property
	def color(self):
		""" Returns virtual Task Color (see Task). """
		scores = [self.DARK_RED, self.RED, self.ORANGE, self.YELLOW, self.GREEN, self.LIGHT_BLUE, self.BRIGHT_BLUE]
		breakpoints = [-20, -10, -1, 1, 5, 10]
		return scores[bisect(breakpoints, self.value)]
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
		raise NotImplementedError
	def undo(self): # pragma: no cover
		""" Marks entry as not completed. """
		raise NotImplementedError

class SubItem(Checkable):
	def __init__(self, _data=None, _api=None, _parent=None):
		self.api = _api
		self._data = _data
		self._parent = _parent
	@property
	def id(self):
		return self._data['id']
	@property
	def parent(self):
		return self._parent
	@property
	def text(self):
		return self._data['text']
	def complete(self):
		""" Marks subitem as completed. """
		if self.is_completed:
			return
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		self._data['completed'] = True
	def undo(self):
		""" Marks subitem as not completed. """
		if not self.is_completed:
			return
		self.api.post('tasks', self._parent.id, 'checklist', self.id, 'score')
		self._data['completed'] = False

class Checklist:
	""" Base class for task that provides list of checkable sub-items. """
	@property
	def checklist(self):
		""" Returns list of task's subitems.
		You can also get subitem directly from task:
		>>> task.checklist[item_id]
		>>> task[item_id]
		"""
		return [SubItem(
			_api=self.api,
			_data=item,
			_parent=self,
			)
			for item
			in self._data['checklist']
			]
	def __getitem__(self, key):
		""" Returns SubItem object for given item index. """
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return SubItem(
					_api=self.api,
					_data=self._data['checklist'][key],
					_parent=self,
					)

class Daily(Task, Checkable, Checklist):
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
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
		self._data['completed'] = True
	def undo(self):
		""" Marks daily as not completed. """
		self.api.post('tasks', self.id, 'score', 'down')
		self._data['completed'] = False

class Todo(Task, Checkable, Checklist):
	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data['notes']
	def complete(self):
		""" Marks todo as completed. """
		self.api.post('tasks', self.id, 'score', 'up')
		self._data['completed'] = True
	def undo(self):
		""" Marks todo as not completed. """
		self.api.post('tasks', self.id, 'score', 'down')
		self._data['completed'] = False

class Spell:
	def __init__(self, _name, _description):
		self._name = _name
		self._description = _description
	@property
	def name(self):
		return self._name
	@property
	def description(self):
		return self._description

class User:
	def __init__(self, _data=None, _api=None, _proxy=None, _content=None):
		self.api = _api
		self.content = _content
		self._data = _data
		self._proxy = _proxy or _UserProxy(_api=self.api, _content=self.content)
	@property
	def stats(self):
		return UserStats(_data=self._data['stats'])
	@property
	def preferences(self):
		return UserPreferences(_data=self._data['preferences'])
	@property
	def inventory(self):
		return Inventory(_data=self._data['items'], _content=self.content)
	def party(self):
		""" Returns user's party. """
		return self._proxy.party()
	def buy(self, item):
		# TODO gold check?
		item._buy(user=self)
	def habits(self):
		return self._proxy.habits()
	def dailies(self):
		return self._proxy.dailies()
	def todos(self):
		return self._proxy.todos()
	def rewards(self):
		return self._proxy.rewards()
	def challenges(self):
		return self._proxy.challenges()
	def spells(self):
		""" Returns list of available spells. """
		SPELLS = { # TODO apparently /content lists these.
			'mage' : {
				Spell('fireball', "Burst of Flames"),
				Spell('mpHeal', "Ethereal Surge"),
				Spell('earth', "Earthquake"),
				Spell('frost', "Chilling Frost"),
				},
			'warrior' : {
				Spell('smash', "Brutal Smash"),
				Spell('defensiveStance', "Defensive Stance"),
				Spell('valorousPresence', "Valorous Presence"),
				Spell('intimidate', "Intimidating Gaze"),
				},
			'rogue' : {
				Spell('pickPocket', "Pickpocket"),
				Spell('backStab', "Backstab"),
				Spell('toolsOfTrade', "Tools of the Trade"),
				Spell('stealth', "Stealth"),
				},
			'healer' : {
				Spell('heal', "Healing Light"),
				Spell('protectAura', "Protective Aura"),
				Spell('brightness', "Searing Brightness"),
				Spell('healAll', "Blessing"),
				},
			}
		return SPELLS[self.stats.class_name]
	def get_spell(self, spell_name):
		""" Returns spell by its short name if available to the user, otherwise None. """
		for spell in self.spells():
			if spell.name == spell_name:
				return spell
		return None
	def cast(self, spell, target=None):
		params = {}
		if target:
			params = {'targetId' : target.id}
		return self.api.post('user', 'class', 'cast', spell.name, **params).data

class _UserProxy:
	def __init__(self, _api=None, _content=None):
		self.api = _api
		self.content = _content
	def __call__(self):
		return User(_data=self.api.get('user').data, _api=self.api, _content=self.content)
	def party(self):
		return Party(_data=self.api.get('groups', 'party').data, _api=self.api)
	def habits(self):
		return [Habit(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='habits').data]
	def dailies(self):
		return [Daily(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='dailys').data]
	def todos(self):
		return [Todo(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='todos').data]
	def rewards(self):
		return [Reward(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='rewards').data]
	def challenges(self):
		return [Challenge(_data=entry, _api=self.api) for entry in self.api.get('challenges', 'user').data]

class Habitica:
	""" Main Habitica entry point. """
	def __init__(self, auth=None, _api=None):
		self.api = _api or api.API(auth['url'], auth['x-api-user'], auth['x-api-key'])
		self._content = None
	def home_url(self):
		""" Returns main Habitica Web URL to open in browser. """
		return self.api.base_url + '/#/tasks'
	def server_is_up(self):
		""" Retruns True if main Habitica service is available. """
		server = self.api.get('status').data
		return server.status == 'up'
	@property
	def content(self):
		if self._content is None:
			self._content = Content(_api=self.api)
		return self._content

	@property
	def user(self):
		""" Returns current user: `habitica.user()`
		May be used as direct proxy to user task list without redundant user() call:
			habitica.user.habits()
			habitica.user.rewards()
		"""
		return _UserProxy(_api=self.api, _content=self.content)
	def groups(self, *group_types):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		result = self.api.get('groups', type=','.join(group_types)).data
		# TODO recognize party and return Party object instead.
		return [Group(_data=entry, _api=self.api) for entry in result]
