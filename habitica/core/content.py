""" Habitica's content: database of all availables items and definitions.
"""
import datetime
from collections import namedtuple
import vintage
from . import base

HabiticaEvent = namedtuple('HabiticaEvent', 'start end')

def parse_habitica_event(data):
	start = datetime.datetime.strptime(data['start'], '%Y-%m-%d').date()
	end = datetime.datetime.strptime(data['end'], '%Y-%m-%d').date()
	return HabiticaEvent(start, end)

class Content(base.ApiInterface):
	""" Cache for all Habitica content. """
	# TODO achievements (pet colors, quest series etc).
	# TODO itemList
	# TODO events
	# TODO bundles (purchaseable quests)
	# TODO questsByLevel
	# TODO appearances
	def __init__(self, _api=None):
		super().__init__(_api=_api, _content=self)
		self._data = self.api.cached('content').get('content').data
	def _get_collection_entry(self, entry_type, collection_name, key=None):
		""" Returns list of all entries from collection.
		If key is specified, returns only that entry.
		"""
		if key:
			return self.child(entry_type, self._data[collection_name][key])
		return self.children(entry_type, self._data[collection_name].values())
	def _get_collection_entry_by_access(self, entry_type, access_list_name, collection_name, key=None, **params):
		""" Returns list of all entries from collection access list.
		If key is specified, returns only that entry.
		NOTE: only entries with allowed access are returned!
		If access is denied for specific key mode, it returns None.
		"""
		if key is not None:
			if self._data[access_list_name].get(key):
				return self.child(entry_type, self._data[collection_name][key])
			return None
		return [self.child(entry_type, self._data[collection_name][key], **params) for key, value in self._data[access_list_name].items() if value]
	@property
	def potion(self):
		return self.child(HealthPotion, self._data['potion'])
	@property
	def armoire(self):
		return self.child(Armoire, self._data['armoire'])
	@property
	def classes(self):
		return self._data['classes']
	@property
	def gearTypes(self):
		return self._data['gearTypes']
	def food(self, key=None):
		return self._get_collection_entry(Food, 'food', key=key)
	def questEggs(self, key=None):
		return self._get_collection_entry(Egg, 'questEggs', key=key)
	def eggs(self, key=None):
		return self._get_collection_entry(Egg, 'eggs', key=key)
	def dropEggs(self, key=None):
		return self._get_collection_entry(Egg, 'dropEggs', key=key)
	def wackyHatchingPotions(self, key=None):
		return self._get_collection_entry(HatchingPotion, 'wackyHatchingPotions', key=key)
	def hatchingPotions(self, key=None):
		return self._get_collection_entry(HatchingPotion, 'hatchingPotions', key=key)
	def dropHatchingPotions(self, key=None):
		return self._get_collection_entry(HatchingPotion, 'dropHatchingPotions', key=key)
	def premiumHatchingPotions(self, key=None):
		return self._get_collection_entry(HatchingPotion, 'premiumHatchingPotions', key=key)
	def petInfo(self, key=None):
		return self._get_collection_entry(Pet, 'petInfo', key=key)
	def questPets(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'questPets', 'petInfo', key=key
				)
	def premiumPets(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'premiumPets', 'petInfo', key=key
				)
	def specialPets(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'specialPets', 'petInfo', key=key,
				_special=True,
				)
	def mountInfo(self, key=None):
		return self._get_collection_entry(Mount, 'mountInfo', key=key)
	def mounts(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'mounts', 'mountInfo', key=key
				)
	def questMounts(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'questMounts', 'mountInfo', key=key
				)
	def premiumMounts(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'premiumMounts', 'mountInfo', key=key
				)
	def specialMounts(self, key=None):
		return self._get_collection_entry_by_access(
				Pet, 'specialMounts', 'mountInfo', key=key,
				_special=True,
				)
	def get_background(self, name):
		return self.child(Background, self._data['backgroundFlats'][name])
	def get_background_set(self, year, month=None):
		""" Returns background set for given year and month.
		If month is None, returns all sets for this year.
		If year is None (explicitly), returns time travel backgrounds.
		"""
		if year is None: # TODO time travel - needs some constant name
			return self.children(Background, self._data['backgrounds']['timeTravelBackgrounds'])
		months = ['{0:02}'.format(month)] if month else ['{0:02}'.format(number) for number in range(1, 13)]
		patterns = ['backgrounds{month}{year}'.format(year=year, month=month) for month in months]
		result = []
		for key in self._data['backgrounds']:
			if key in patterns:
				result += self.children(Background, self._data['backgrounds'][key])
		return result
	def special_items(self, key=None):
		return self._get_collection_entry(SpecialItem, 'special', key=key)
	def cards(self):
		return [self.child(SpecialItem, self._data['special'][key]) for key in self._data['cardTypes'].keys()]
	def spells(self, class_name):
		return self.children(Spell, self._data['spells'][class_name].values())
	def get_spell(self, class_name, spell_key):
		return self.child(Spell, self._data['spells'][class_name][spell_key])
	@property
	def userCanOwnQuestCategories(self):
		return self._data['userCanOwnQuestCategories']
	def quests(self, key):
		from .quests import Quest
		return self.child(Quest, self._data['quests'][key])
	def get_quest(self, quest_key):
		from .quests import Quest
		return self.child(Quest, self._data['quests'][quest_key])
	def gear(self, key):
		return self.child(Gear, self._data['gear']['flat'][key])
	def gear_tree(self, gear_type, gear_class, gear_index):
		return self.child(Gear, self._data['gear']['tree'][gear_type][gear_class][gear_index])
	def mystery(self, key):
		return self._get_collection_entry(MysterySet, 'mystery', key=key)
	def __getitem__(self, key):
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return self._data[key]

class ContentEntry(base.ApiObject):
	""" Base class for all content entries. """
	def __repr__(self): # pragma: no cover
		return '{0}({1})'.format(type(self).__name__, repr(self.key))
	def __str__(self):
		return self.text
	@property
	def key(self):
		return self._data['key']
	@property
	def text(self):
		return self._data['text']
	@property
	def notes(self):
		return self._data.get('notes', '')

class Marketable:
	""" Mixin for objects that can be bought (at market, from time travellers etc).
	Supports both properties .cost and .price (return the same Price object).
	Searches for 'value', 'cost', 'price' in object's data.
	If there is no specific currency in data, searches for a class field .CURRENCY.
	See alse MarketableFor<CurrencyType> descendants.
	"""
	CURRENCY = NotImplemented
	@property
	def cost(self):
		return base.Price(
				self._data.get('value',
					self._data.get('price')
					),
				self._data.get('currency', self.CURRENCY)
				)
	@property
	def price(self):
		return self.cost
	@property
	def value(self):
		return self.cost
	@property
	@vintage.deprecated('Use .cost.currency')
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.cost.currency

class MarketableForGold(Marketable):
	CURRENCY = 'gold'

class MarketableForGems(Marketable):
	CURRENCY = 'gems'

class BaseStats:
	""" Base character stats. """
	@property
	def int(self):
		return self._data['int']
	@property
	def intelligence(self):
		return self.int
	@property
	def str(self):
		return self._data['str']
	@property
	def strength(self):
		return self.str
	@property
	def per(self):
		return self._data['per']
	@property
	def perception(self):
		return self.per
	@property
	def con(self):
		return self._data['con']
	@property
	def constitution(self):
		return self.con

class Armoire(ContentEntry, MarketableForGold):
	@property
	def type(self):
		return self._data['type']

class Egg(ContentEntry, MarketableForGems):
	@property
	def mountText(self):
		return self._data['mountText']
	@property
	def adjective(self):
		return self._data['adjective']

class HatchingPotion(ContentEntry, MarketableForGems):
	@property
	def _addlNotes(self):
		return self._data.get('_addlNotes', '')
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
		return parse_habitica_event(self._data['event'])

class Food(ContentEntry, MarketableForGems):
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
	def canDrop(self):
		return self._data['canDrop']

class Background(ContentEntry, MarketableForGems):
	@property
	def set_name(self):
		return self._data['set']

class HealthOverflowError(Exception):
	def __init__(self, hp, maxHealth):
		self.hp, self.maxHealth = hp, maxHealth
	def __str__(self):
		return 'HP is too high, part of health potion would be wasted.'

class HealthPotion(ContentEntry, MarketableForGold):
	""" Health potion (+15 hp). """
	VALUE = 15.0
	def __init__(self, overflow_check=True, **kwargs):
		""" If overflow_check is True and there is less than 15 hp damage,
		so buying potion will result in hp bar overflow and wasting of potion,
		raises HealthOverflowError.
		"""
		super().__init__(**kwargs)
		self.overflow_check = overflow_check
	@property
	def type(self):
		return self._data['type']
	def _buy(self, user):
		if self.overflow_check and float(user.stats.hp) + self.VALUE > user.stats.maxHealth:
			raise HealthOverflowError(user.stats.hp, user.stats.maxHealth)
		user._data = self.api.post('user', 'buy-health-potion').data

class StableCreature(ContentEntry):
	""" Base class for Pets and Mounts. """
	def __init__(self, _special=None, **kwargs):
		super().__init__(**kwargs)
		self._special = _special
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

class Pet(StableCreature):
	pass

class Mount(StableCreature):
	pass

class Castable:
	@property
	def mana(self):
		return self._data['mana']
	@property
	def target(self):
		""" 'self', 'user', 'party', 'task' """
		return self._data['target']

class SpecialItem(ContentEntry, MarketableForGold, Castable):
	""" Cards, seeds, sparkles, debuff potions etc. """
	@property
	def purchaseType(self):
		return self._data.get('purchaseType')
	@property
	def previousPurchase(self):
		return self._data.get('previousPurchase', False)
	@property
	def silent(self):
		return self._data.get('silent', False)
	@property
	def immediateUse(self):
		return self._data.get('immediateUse', False)
	@property
	def yearRound(self):
		card =  self.content['cardTypes'].get(self.key)
		if not card:
			return False
		return card['yearRound']
	@property
	def messageOptions(self):
		card =  self.content['cardTypes'].get(self.key)
		if not card:
			return None
		return card['messageOptions']

class Spell(ContentEntry, Castable):
	@property
	@vintage.deprecated('Use spell.key instead')
	def name(self): # pragma: no cover -- kept for backward compatibility.
		return self.key
	@property
	@vintage.deprecated('Use spell.text instead')
	def description(self): # pragma: no cover -- kept for backward compatibility.
		return self.text
	@property
	def lvl(self):
		return self._data['lvl']

class Gear(ContentEntry, BaseStats, MarketableForGold):
	@property
	def klass(self):
		return self._data['klass']
	@property
	def class_name(self):
		if self.is_special and 'specialClass' in self._data:
			return self._data['specialClass']
		return self.klass
	@property
	def specialClass(self):
		return self._data.get('specialClass')
	@property
	def is_special(self):
		return 'specialClass' in self._data
	@property
	def type(self):
		return self._data['type']
	@property
	def index(self):
		return self._data['index']
	@property
	def set_name(self):
		return self._data['set']
	@property
	def gearSet(self):
		return self._data.get('gearSet')
	@property
	def event(self):
		if 'event' not in self._data:
			return None
		return parse_habitica_event(self._data['event'])
	@property
	def mystery(self):
		return self._data.get('mystery')
	@property
	def twoHanded(self):
		return self._data.get('twoHanded', False)
	@property
	def last(self):
		return self._data.get('last', False)

class MysterySet(ContentEntry):
	@property
	def class_name(self):
		return self._data['class']
	@property
	def event(self):
		return parse_habitica_event(self._data) # Reads only 'start' and 'end'
	@property
	def start(self): # TODO subclass HabiticaEvent.
		return self.event.start
	@property
	def end(self): # TODO subclass HabiticaEvent.
		return self.event.end
	def items(self):
		return self.children(Gear, self._data['items'])
