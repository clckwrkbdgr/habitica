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

class Inventory(base.ApiObject):
	@property
	def food(self):
		return [content.Food(_api=self.api, _data=entry) for entry in self._data['food']]
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

class User(base.ApiObject):
	def __init__(self, _proxy=None, **kwargs):
		super().__init__(**kwargs)
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
		return groups.Party(_data=self.api.get('groups', 'party').data, _api=self.api)
	def habits(self):
		return [tasks.Habit(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='habits').data]
	def dailies(self):
		return [tasks.Daily(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='dailys').data]
	def todos(self):
		return [tasks.Todo(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='todos').data]
	def rewards(self):
		return [tasks.Reward(_data=entry, _api=self.api) for entry in self.api.get('tasks', 'user', type='rewards').data]
	def challenges(self):
		return [groups.Challenge(_data=entry, _api=self.api) for entry in self.api.get('challenges', 'user').data]
