import os
import json
import time
from bisect import bisect
from pathlib import Path
from functools import lru_cache
from . import api, config
from . import timeutils

# Weekday abbreviations used in task frequencies.
HABITICA_WEEK = ["m", "t", "w", "th", "f", "s", "su"]

class Content:
	""" Cache for all Habitica content. """
	def __init__(self, _api=None):
		self.api = _api
		self.cache_file = Path(config.get_cache_dir())/"content.cache.json"
		if not self.cache_file.exists() or time.time() > self.cache_file.stat().st_mtime + 60*60*24: # TODO how to invalidate Habitica content cache?
			self._data = self.api.get('content').data
			self.cache_file.write_text(json.dumps(self._data))
		else:
			self._data = json.loads(self.cache_file.read_text())
	def __getitem__(self, key):
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return self._data[key]

class ChatMessage:
	def __init__(self, _data=None):
		self._data = _data
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
		return int(self._data['timestamp'])
	@property
	def text(self):
		return self._data['text']

class Group:
	""" Habitica's user group: a guild, a party, the Tavern. """
	PARTY = 'party'
	GUILDS = 'guilds'
	PRIVATE_GUILDS = 'privateGuilds'
	PUBLIC_GUILDS = 'publicGuilds'
	TAVERN = 'tavern'

	def __init__(self, _data=None, _api=None):
		self.api = _api
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def name(self):
		return self._data['name']
	def chat(self):
		return [ChatMessage(entry) for entry in self.api.get('groups', self.id, 'chat').data]
	def mark_chat_as_read(self):
		self.api.post('groups', self.id, 'chat', 'seen')

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
			try:
				quest_progress = list(qp_tmp.values())[0]['count']
			except TypeError:
				quest_progress = list(qp_tmp.values())[0]
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
		return self._data['toNextLevel']
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
	def __init__(self, overflow_check=True, _hbt=None):
		""" If overflow_check is True and there is less than 15 hp damage,
		so buying potion will result in hp bar overflow and wasting of potion,
		raises HealthOverflowError.
		"""
		self.hbt = _hbt
		self.overflow_check = overflow_check
	def _buy(self, user):
		if self.overflow_check and user.stats.hp + self.VALUE > user.stats.maxHealth:
			raise HealthOverflowError(user.stats.hp, user.stats.maxHealth)
		self._data = self.hbt.user['buy-health-potion'](_method='post')

class Pet:
	def __init__(self, _data=None):
		self._data = _data
	def __str__(self):
		return self._data

class Mount:
	def __init__(self, _data=None):
		self._data = _data
	def __str__(self):
		return self._data

class Inventory:
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
	@property
	def food(self):
		return [Item(_data=entry) for entry in self._data['food']]
	@property
	def pet(self):
		return Pet(_data=self._data['currentPet'])
	@property
	def mount(self):
		return Mount(_data=self._data['currentMount'])

class Reward:
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
	@property
	def text(self):
		return self._data['text']
	def _buy(self, user):
		self.hbt.tasks[self._data['id']].score(_direction='up', _method='post')

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
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
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
		tval = self._data['value']
		result = self.hbt.tasks[self._data['id']].score(_direction='up', _method='post')
		self._data['value'] += result['delta']
	def down(self):
		if not self._data['down']:
			raise CannotScoreDown(self)
		tval = self._data['value']
		result = self.hbt.tasks[self._data['id']].score(_direction='down', _method='post')
		self._data['value'] += result['delta']

class Checkable:
	""" Base class for task or sub-item that can be checked (completed) or unchecked.
	"""
	@property
	def is_completed(self):
		return self._data['completed']
	def complete(self):
		""" Marks entry as completed. """
		raise NotImplementedError
	def undo(self):
		""" Marks entry as not completed. """
		raise NotImplementedError

class SubItem(Checkable):
	def __init__(self, _data=None, _hbt=None, _parent=None):
		self.hbt = _hbt
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
		self.hbt.tasks[self._parent._data['id']]['checklist'][self._data['id']].score(
					   _method='post')
		self._data['completed'] = True
	def undo(self):
		""" Marks subitem as not completed. """
		if not self.is_completed:
			return
		self.hbt.tasks[self._parent._data['id']]['checklist'][self._data['id']].score(
					   _method='post')
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
			_hbt=self.hbt,
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
					_hbt=self.hbt,
					_data=self._data['checklist'][key],
					_parent=self,
					)

class Daily(Task, Checkable, Checklist):
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
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
		else:
			raise ValueError("Unknown daily frequency: {0}".format(self._data['frequency']))
		return True

	def complete(self):
		""" Marks daily as completed. """
		self.hbt.tasks[self._data['id']].score(
				_direction='up', _method='post')
		self._data['completed'] = True
	def undo(self):
		""" Marks daily as not completed. """
		self.hbt.tasks[self._data['id']].score(
				_direction='down', _method='post')
		self._data['completed'] = False

class Todo(Task, Checkable, Checklist):
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
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
		self.hbt.tasks[self._data['id']].score(
				_direction='up', _method='post')
		self._data['completed'] = True
	def undo(self):
		""" Marks todo as not completed. """
		self.hbt.tasks[self._data['id']].score(
				_direction='down', _method='post')
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
	def __init__(self, _data=None, _hbt=None, _api=None, _proxy=None):
		self.hbt = _hbt
		self.api = _api
		self._data = _data
		self._proxy = _proxy or _UserProxy(_hbt=self.hbt, _api=self.api)
	@property
	def stats(self):
		return UserStats(_data=self._data['stats'])
	@property
	def preferences(self):
		return UserPreferences(_data=self._data['preferences'])
	@property
	def inventory(self):
		return Inventory(_data=self._data['items'])
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
		return self._proxy.dailies()
	def rewards(self):
		return self._proxy.rewards()
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
		return self.hbt.user['class']['cast'][spell.name](**params, _method='post')

class _UserProxy:
	def __init__(self, _hbt=None, _api=None):
		self.hbt = _hbt
		self.api = _api
	def __call__(self):
		return User(_data=self.hbt.user(), _hbt=self.hbt, _api=self.api)
	def party(self):
		return Party(_data=self.api.get('groups', 'party').data, _api=self.api)
	def habits(self):
		return [Habit(_data=entry, _hbt=self.hbt) for entry in self.hbt.tasks.user(type='habits')]
	def dailies(self):
		return [Daily(_data=entry, _hbt=self.hbt) for entry in self.hbt.tasks.user(type='dailys')]
	def todos(self):
		return [Todo(_data=entry, _hbt=self.hbt) for entry in self.hbt.tasks.user(type='todos')]
	def rewards(self):
		return [Reward(_data=entry, _hbt=self.hbt) for entry in self.hbt.tasks.user(type='rewards')]

class Habitica:
	""" Main Habitica entry point. """
	def __init__(self, auth=None):
		self.api = api.API(auth['url'], auth['x-api-user'], auth['x-api-key'])

		self.auth = auth
		self.cache = config.Cache()
		self.hbt = api.Habitica(auth=auth, _api=self.api)
	def home_url(self):
		""" Returns main Habitica Web URL to open in browser. """
		return self.api.base_url + '/#/tasks'
	def server_is_up(self):
		""" Retruns True if main Habitica service is available. """
		server = self.api.get('status').data
		return server.status == 'up'
	def content(self):
		return Content(_api=self.api)

	@property
	def user(self):
		""" Returns current user: `habitica.user()`
		May be used as direct proxy to user task list without redundant user() call:
			habitica.user.habits()
			habitica.user.rewards()
		"""
		return _UserProxy(_hbt=self.hbt, _api=self.api)
	def groups(self, *group_types):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		result = self.hbt.groups(type=','.join(group_types))
		# TODO recognize party and return Party object instead.
		return [Group(_data=entry, _api=self.api) for entry in result]
