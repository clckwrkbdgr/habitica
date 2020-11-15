import os
import json
import time
from pathlib import Path
from . import api, config

HEALTH_POTION_VALUE = 15.0

class Content:
	""" Cache for all Habitica content. """
	def __init__(self, _hbt=None):
		self.hbt = _hbt
		self.cache_file = Path(config.get_cache_dir())/"content.cache.json"
		if not self.cache_file.exists() or time.time() > self.cache_file.stat().st_mtime + 60*60*24: # TODO how to invalidate Habitica content cache?
			self._data = self.hbt.content()
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

	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
	@property
	def id(self):
		return self._data['id']
	@property
	def name(self):
		return self._data['name']
	def chat(self):
		return [ChatMessage(entry) for entry in self.hbt.groups[self.id].chat()]
	def mark_chat_as_read(self):
		self.hbt.groups[self.id]['chat'].seen(_method='post')

class Quest:
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
	@property
	def active(self):
		return bool(self._data['active'])
	@property
	def key(self):
		return self._data['key']

class Party(Group):
	def __init__(self, _data=None, _hbt=None):
		super().__init__(_data=_data, _hbt=_hbt)
	@property
	def quest(self):
		return Quest(_data=self._data['quest'], _hbt=self.hbt)

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

class User:
	def __init__(self, _data=None, _hbt=None):
		self.hbt = _hbt
		self._data = _data
	@property
	def stats(self):
		return UserStats(_data=self._data['stats'])
	@property
	def inventory(self):
		return Inventory(_data=self._data['items'])
	def party(self):
		""" Returns user's party. """
		return Party(_data=self.hbt.groups.party(), _hbt=self.hbt)
	def buy_health_potion(self, overflow_check=True):
		""" Buys health potion (+15hp).

		If overflow_check is True and there is less than 15 hp damage,
		so buying potion will result in hp bar overflow and wasting of potion,
		raises HealthOverflowError.
		"""
		# TODO gold check?
		if overflow_check and self.stats.hp + HEALTH_POTION_VALUE > self.stats.maxHealth:
			raise HealthOverflowError(self.stats.hp, self.stats.maxHealth)
		self._data = self.hbt.user['buy-health-potion'](_method='post')

class Habitica:
	""" Main Habitica entry point. """
	def __init__(self, auth=None):
		self.api = api.API(auth['url'], auth['x-api-user'], auth['x-api-key'])

		self.auth = auth
		self.cache = config.Cache()
		self.hbt = api.Habitica(auth=auth)
	def home_url(self):
		""" Returns main Habitica Web URL to open in browser. """
		return self.api.base_url + '/#/tasks'
	def server_is_up(self):
		""" Retruns True if main Habitica service is available. """
		server = self.hbt.status()
		return server['status'] == 'up'
	def content(self):
		return Content(_hbt=self.hbt)

	def user(self):
		""" Returns current user. """
		return User(_data=self.hbt.user(), _hbt=self.hbt)
	def groups(self, *group_types):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		result = self.hbt.groups(type=','.join(group_types))
		# TODO recognize party and return Party object instead.
		return [Group(_data=entry, _hbt=self.hbt) for entry in result]
