""" Groups and related functionality: chats, challenges.
"""
from functools import lru_cache
from collections import defaultdict
from . import base, content, tasks, quests, user

def iterate_pages(api_obj, class_type, *get_request_path, _limit=30, **query_params):
	""" Loads paged entities via GET request.
	Yields produced objects of class_type.
	Produced object should support field .id
	Request should support optional 'lastId'
	"""
	batch = api_obj.children(class_type, api_obj.api.get(*get_request_path, **query_params).data)
	lastId = batch[-1].id
	while len(batch) >= _limit:
		for entity in batch:
			yield entity
		batch = api_obj.children(class_type, api_obj.api.get(*get_request_path, lastId=lastId, **query_params).data)
		lastId = batch[-1].id
	for entity in batch:
		yield entity

class Challenge(base.Entity):
	# TODO get challenge by id: get:/challenges/:id
	# TODO .categories
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
	def description(self):
		return self._data['description']
	@property
	def updatedAt(self):
		return self._data['updatedAt'] # FIXME convert to date time using user TZ.
	@property
	def createdAt(self):
		return self._data['createdAt'] # FIXME convert to date time using user TZ.
	@property
	def prize(self):
		return base.Price(self._data['prize'], 'gems')
	@property
	def memberCount(self):
		return self._data['memberCount']
	@property
	def official(self):
		return self._data['official']
	# TODO GET /tasks/challenge/:id ? type=[daily,...]
	def rewards(self):
		return [self.child(tasks.Reward, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['rewards']]
	def todos(self):
		return [self.child(tasks.Todo, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['todos']]
	def dailies(self):
		return [self.child(tasks.Daily, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['dailys']]
	def habits(self):
		return [self.child(tasks.Habit, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['habits']]
	def create_task(self, task_obj):
		data = self.api.post('tasks', 'challenge', self.id, _body=task_obj._data).data
		return self.child(tasks.Task.type_from_str(data['type']), data)
	def leader(self):
		return self.child(user.Member, self.api.get('members', self._data['leader']).data)
	def member(self, id):
		return self.child(user.Member, self.api.get('challenges', self.id, 'members', id).data)
	def members(self, includeAllPublicFields=False, includeTasks=False):
		""" Yields all current invites for the group. """
		for member in iterate_pages(self, user.Member, 'challenges', self.id, 'members', includeAllPublicFields=includeAllPublicFields, includeTasks=includeTasks):
			yield member
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

class ChatMessage(base.Entity):
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

class Group(base.Entity):
	""" Habitica's user group: a guild, a party, the Tavern. """
	PARTY = 'party'
	GUILDS = 'guilds'
	PRIVATE_GUILDS = 'privateGuilds'
	PUBLIC_GUILDS = 'publicGuilds'
	TAVERN = 'tavern'

	PRIVATE, PUBLIC = 'private', 'public'

	# TODO .categories
	# TODO .managers (Mixed)
	@property
	def name(self):
		return self._data['name']
	@property
	def summary(self):
		return self._data['summary']
	@property
	def description(self):
		return self._data['description']
	@property
	def type(self):
		return self._data['type']
	@property
	def privacy(self):
		return self._data['privacy']
	@property
	def is_public(self):
		return self.privacy == 'public'
	@property
	def bannedWordsAllowed(self):
		return self._data['bannedWordsAllowed']
	@property
	def leaderOnly(self):
		""" {.challenges, .getGems} """
		return self._data['leaderOnly']
	def leader(self):
		return self.child(user.Member, self.api.get('members', self._data['leader']).data)
	@property
	def memberCount(self):
		return self._data['memberCount']
	@property
	def challengeCount(self):
		return self._data['challengeCount']
	@property
	def balance(self):
		return base.Price(self._data['balance'], 'gems')
	@property
	def logo(self):
		return self._data['logo']
	@property
	def leaderMessage(self):
		return self._data['leaderMessage']
	# TODO GET /tasks/group/:id ? type=[daily,...]
	def rewards(self):
		return [self.child(tasks.Reward, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['rewards']]
	def todos(self):
		return [self.child(tasks.Todo, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['todos']]
	def dailies(self):
		return [self.child(tasks.Daily, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['dailys']]
	def habits(self):
		return [self.child(tasks.Habit, self.api.get('tasks', task_id).data) for task_id in self._data['tasksOrder']['habits']]
	def create_task(self, task_obj):
		data = self.api.post('tasks', 'group', self.id, _body=task_obj._data).data
		return self.child(tasks.Task.type_from_str(data['type']), data)
	def challenges(self):
		return self.children(Challenge, self.api.get('challenges', 'groups', self.id).data)
	@property
	def chat(self):
		return self.child_interface(Chat)
	def update(self, **kwargs): # pragma: no cover -- TODO API docs have no description for params of this method at all.
		self._data = self.api.put('groups', group.id, _body=kwargs)
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
	def add_manager(self, member):
		self.api.post('groups', self.id, 'add-manager', _body={
			'managerId' : member.id,
			})
	def remove_manager(self, member):
		self.api.post('groups', self.id, 'remove-manager', _body={
			'managerId' : member.id,
			})
	def invite(self, *users):
		""" Invites any number of users, but at least one.
		User either has to be a Member, or an externa Email.
		"""
		assert users
		params = defaultdict(list)
		for invited in users:
			if isinstance(invited, user.Email):
				email = {
						'email' : invited.email,
						}
				if invited.name:
					email['name'] = invited.name
				params['emails'].append(email)
			elif isinstance(invited, user.Member):
				params['uuids'].append(invited.id)
			else:
				raise ValueError("Value is not a Member or an Email: {0}".format(repr(invited)))
		# TODO It returns array of successful invites (email&members),
		# but what is it useful for?
		self.api.post('groups', self.id, 'invite', _body=params)
	def all_invites(self, includeAllPublicFields=False):
		""" Yields all current invites for the group. """
		for member in iterate_pages(self, user.Member, 'groups', self.id, 'invites', includeAllPublicFields=includeAllPublicFields):
			yield member
	def approvals(self): # pragma: no cover -- TODO no scenario
		return [
				self.child(tasks.Task.type_from_str(data['type']), data)
				for data in
				self.api.get('approvals', 'group', self.id).data
				]
	def members(self, includeAllPublicFields=False, includeTasks=False):
		""" Yields all current invites for the group. """
		for member in iterate_pages(self, user.Member, 'groups', self.id, 'members', includeAllPublicFields=includeAllPublicFields, includeTasks=includeTasks):
			yield member
	def removeMember(self, member, message=''):
		self.api.post('groups', self.id, 'removeMember', member.id, message=message)


class Party(Group):
	@property
	def quest(self):
		return self.child(quests.Quest, None, _group_progress=self._data['quest'])
	def invite_to_quest(self, quest):
		self._data['quest'] = self.api.post('groups', self.id, 'quests', 'invite', quest.key).data
