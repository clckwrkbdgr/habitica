from . import api, config

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

	def groups(self, *group_types):
		result = self.hbt.groups(type=','.join(group_types))
		return [Group(_data=entry, _hbt=self.hbt) for entry in result]
