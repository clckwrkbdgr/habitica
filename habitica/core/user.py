""" User and user-related functionality: inventory, spells etc.
"""
from . import base, content, tasks, groups

class UserPreferences(base.ApiObject):
	@property
	def timezoneOffset(self):
		return self._data['timezoneOffset']

class UserStats(base.ApiObject):
	@property
	def class_name(self):
		return self._data['class']
	@property
	def hp(self):
		return base.ValueBar(self._data['hp'], self._data['maxHealth'])
	@property
	def maxHealth(self): # pragma: no cover -- FIXME deprecated
		return self.hp.max_value
	@property
	def level(self):
		return self._data['lvl']
	@property
	def experience(self):
		return base.ValueBar(self._data['exp'],
				self._data['exp'] + self._data['toNextLevel'],
				)
	@property
	def maxExperience(self): # pragma: no cover -- FIXME deprecated
		return self.experience.max_value
	@property
	def mana(self):
		return base.ValueBar(self._data['mp'], self._data['maxMP'])
	@property
	def maxMana(self): # pragma: no cover -- FIXME deprecated
		return self.mana.max_value
	@property
	def gold(self):
		return self._data['gp']

class Inventory(base.ApiObject):
	@property
	def food(self):
		return self.children(content.Food, self._data['food'])
	@property
	def pet(self):
		return self.content.petInfo(self._data['currentPet']) if self._data['currentPet'] else None
	@property
	def mount(self):
		return self.content.mountInfo(self._data['currentMount']) if self._data['currentMount'] else None

class _UserMethods:
	""" Trait to be used by ApiObject or ApiInterface
	to access user methods that do not require user data.
	"""
	def party(self):
		""" Returns user's party. """
		return self.child(groups.Party, self.api.get('groups', 'party').data)
	def group_plans(self):
		return self.children(groups.Group, self.api.get('group-plans').data)
	def join(self, group):
		group._data = self.api.post('groups', group.id, 'join').data
	def leave(self, group, keep_tasks=True, leave_challenges=True):
		self.api.post('groups', group.id, 'leave', keep='keep-all' if keep_tasks else 'remove-all', _body={
			'keepChallenges' : 'leave-challenges' if leave_challenges else 'remain-in-challenges'
			})
	def reject_invite(self, group):
		self.api.post('groups', group.id, 'reject-invite').data

	def habits(self):
		return self.children(tasks.Habit, self.api.get('tasks', 'user', type='habits').data)
	def dailies(self):
		return self.children(tasks.Daily, self.api.get('tasks', 'user', type='dailys').data)
	def todos(self):
		return self.children(tasks.Todo, self.api.get('tasks', 'user', type='todos').data)
	def rewards(self):
		return self.children(tasks.Reward, self.api.get('tasks', 'user', type='rewards').data)
	def challenges(self):
		return self.children(groups.Challenge, self.api.get('challenges', 'user').data)

class UserProxy(base.ApiInterface, _UserMethods):
	""" Lazy class to proxy call methods that do not require immediate user data,
	like lists of tasks, challenges, user's party etc:
	   habitica.user.todos()
	   habitica.user.party()
	   ...
	To get real User out of this proxy, call this object like a method:
	   real_user = habitica.user()
	   real_user.todos()
	   real_user.party()
	   ...
	"""
	def __call__(self):
		return self.child(User, self.api.get('user').data, _parent=self._parent)

class Email:
	""" External person: only e-mail and optional name.
	Used mostly for invites.
	"""
	def __init__(self, email, name=None):
		self.email = email
		self.name = name

class Member(base.ApiObject):
	""" All other Habitica users beside you. """
	@property
	def id(self):
		return self._data.get('_id', self._data.get('id'))
	@property
	def name(self):
		return self._data.get('profile', {}).get('name')
	@property
	def preferences(self):
		return self._data.get('preferences', {})
	@property
	def inbox(self):
		return self._data.get('inbox', {})
	@property
	def stats(self):
		return self._data.get('stats', {})
	@property
	def items(self):
		return self._data.get('items', {})
	@property
	def achievements(self):
		return self._data.get('achievements', {})
	@property
	def auth(self):
		return self._data.get('auth', {})
	def party(self):
		return self.child(groups.Party, self._data.get('party', {}))
	def tasks(self):
		return self.children(tasks.Task, self._data.get('tasks', []))

class User(base.ApiObject, _UserMethods):
	@property
	def id(self):
		return self._data.get('_id', self._data.get('id'))
	@property
	def stats(self):
		return UserStats(_data=self._data['stats'])
	@property
	def preferences(self):
		return UserPreferences(_data=self._data['preferences'])
	@property
	def inventory(self):
		return Inventory(_data=self._data['items'], _content=self.content)
	def avatar(self):
		""" Returns pure HTML code to render user avatar.
		Behavior may change in the future.
		"""
		# TODO Rendering avatar as PNG is broken for years.
		# TODO There are also other (private) methods on /export/ route.
		# TODO Render as image and cache.
		return self.api.get('export', 'avatar-{0}.html'.format(self.id), _as_json=False)
	def buy(self, item):
		# TODO gold check?
		item._buy(user=self)
	def spells(self):
		""" Returns list of available spells. """
		return self.content.spells(self.stats.class_name)
	def get_spell(self, spell_key):
		""" Returns spell by its spell key if available to the user, otherwise None. """
		return self.content.get_spell(self.stats.class_name, spell_key)
	def cast(self, spell, target=None):
		params = {}
		if target:
			params = {'targetId' : target.id}
		return self.api.post('user', 'class', 'cast', spell.key, **params).data
