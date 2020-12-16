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

class _UserMethods:
	""" Trait to be used by ApiObject or ApiInterface
	to access user methods that do not require user data.
	"""
	def party(self):
		""" Returns user's party. """
		return self.child(groups.Party, self.api.get('groups', 'party').data)
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

class User(base.ApiObject, _UserMethods):
	@property
	def stats(self):
		return UserStats(_data=self._data['stats'])
	@property
	def preferences(self):
		return UserPreferences(_data=self._data['preferences'])
	@property
	def inventory(self):
		return Inventory(_data=self._data['items'], _content=self.content)
	def buy(self, item):
		# TODO gold check?
		item._buy(user=self)
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
