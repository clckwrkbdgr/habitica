""" Groups and related functionality: chats, challenges.
"""
from functools import lru_cache
from . import base, content, tasks

class Challenge(base.ApiObject):
	# TODO get challenge by id: get:/challenges/:id
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
		return [self.child(tasks.Reward, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['rewards']]
	def todos(self):
		return [self.child(tasks.Todo, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['todos']]
	def dailies(self):
		return [self.child(tasks.Daily, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['dailys']]
	def habits(self):
		return [self.child(tasks.Habit, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['habits']]
	def leader(self):
		# FIXME get person profile by id.
		return self._data['leader']
	def group(self):
		# FIXME get group by id.
		return self.child(Group, self._data['group'])
	def as_csv(self):
		return self.api.get('challenges', self.id, 'export', 'csv')
	def clone(self):
		return self.child(Challenge, self.api.post('challenges', self.id, 'clone').challenge, _parent=self)
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

class ChatMessage(base.ApiObject):
	@property
	def id(self):
		return self._data['id']
	@property
	def group(self):
		return self._parent
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

class Chat(base.ApiInterface):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self._entries = None
	def __call__(self):
		return self.messages()
	@property
	def group(self):
		return self._parent
	def messages(self):
		if self._entries is None:
			self._entries = self.children(ChatMessage, self.api.get('groups', self.group.id, 'chat').data, _parent=self.group)
		return self._entries
	def mark_as_read(self):
		self.api.post('groups', self.group.id, 'chat', 'seen')
	def delete(self, message):
		if self._entries:
			new_entries = self.api.delete('groups', self.group.id, 'chat', message.id, previousMsg=self._entries[-1].id).data
			self._entries = self.children(ChatMessage, new_entries, _parent=self.group)
		else:
			self.api.delete('groups', self.group.id, 'chat', message.id)
	def post(self, message_text):
		if self._entries:
			new_entries = self.api.post('groups', self.group.id, 'chat', previousMsg=self._entries[-1].id,  _body={'message':message_text}).data
		else:
			new_entries = self.api.post('groups', self.group.id, 'chat', _body={'message':message_text}).data
		self._entries = self.children(ChatMessage, new_entries, _parent=self.group)

class Group(base.ApiObject):
	""" Habitica's user group: a guild, a party, the Tavern. """
	PARTY = 'party'
	GUILDS = 'guilds'
	PRIVATE_GUILDS = 'privateGuilds'
	PUBLIC_GUILDS = 'publicGuilds'
	TAVERN = 'tavern'

	PRIVATE, PUBLIC = 'private', 'public'

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
		return self.children(Challenge, self.api.get('challenges', 'groups', self.id).data)
	@property
	def chat(self):
		return self.child_interface(Chat)
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
		return self.child(Challenge, data)

class Quest(base.ApiObject):
	@lru_cache()
	def _quest_content(self):
		return self.content['quests'][self.key]
	@property
	def active(self):
		return bool(self._data['active'])
	@property
	def key(self):
		return self._data['key']
	@property
	def title(self):
		return self._quest_content()['text']
	@property
	def progress(self):
		content = self._quest_content()
		if content.get('collect'):
			qp_tmp = self._data['progress']['collect']
			quest_progress = sum(qp_tmp.values())
			return base.ValueBar(
					quest_progress,
					sum([int(item['count']) for item in content['collect'].values()]),
					)
		else:
			return base.ValueBar(
					self._data['progress']['hp'],
					content['boss']['hp'],
					)
	@property
	def max_progress(self): # pragma: no cover -- FIXME deprecated
		return self.progress.max_value

class Party(Group):
	@property
	def quest(self):
		return self.child(Quest, self._data['quest'])
