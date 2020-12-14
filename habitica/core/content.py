""" Habitica's content: database of all availables items and definitions.
"""
import datetime
from collections import namedtuple
from . import base

HabiticaEvent = namedtuple('HabiticaEvent', 'start end')

class Content(base.ApiInterface):
	""" Cache for all Habitica content. """
	def __init__(self, _api=None):
		super().__init__(_api=_api, _content=self)
		self._data = self.api.cached('content').get('content').data
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
	def questEggs(self):
		return self.children(Egg, self._data['questEggs'].values())
	def eggs(self):
		return self.children(Egg, self._data['eggs'].values())
	def dropEggs(self):
		return self.children(Egg, self._data['dropEggs'].values())
	def wackyHatchingPotions(self):
		return self.children(HatchingPotion, self._data['wackyHatchingPotions'].values())
	def hatchingPotions(self):
		return self.children(HatchingPotion, self._data['hatchingPotions'].values())
	def dropHatchingPotions(self):
		return self.children(HatchingPotion, self._data['dropHatchingPotions'].values())
	def premiumHatchingPotions(self):
		return self.children(HatchingPotion, self._data['premiumHatchingPotions'].values())
	def petInfo(self, key=None):
		if key:
			return self.child(Pet, self._data['petInfo'][key])
		return self.children(Pet, self._data['petInfo'].values())
	def questPets(self):
		return [self.child(Pet, self._data['petInfo'][key]) for key, value in self._data['questPets'].items() if value]
	def premiumPets(self):
		return [self.child(Pet, self._data['petInfo'][key]) for key, value in self._data['premiumPets'].items() if value]
	def specialPets(self):
		return [self.child(Pet, self._data['petInfo'][key], _special=value) for key, value in self._data['specialPets'].items() if value]
	def mountInfo(self, key=None):
		if key:
			return self.child(Mount, self._data['mountInfo'][key])
		return self.children(Mount, self._data['mountInfo'].values())
	def mounts(self):
		return [self.child(Mount, self._data['mountInfo'][key]) for key, value in self._data['mounts'].items() if value]
	def questMounts(self):
		return [self.child(Mount, self._data['mountInfo'][key]) for key, value in self._data['questMounts'].items() if value]
	def premiumMounts(self):
		return [self.child(Mount, self._data['mountInfo'][key]) for key, value in self._data['premiumMounts'].items() if value]
	def specialMounts(self):
		return [self.child(Mount, self._data['mountInfo'][key], _special=value) for key, value in self._data['specialMounts'].items() if value]
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
	def __getitem__(self, key):
		try:
			return object.__getitem__(self, key)
		except AttributeError:
			return self._data[key]

class Armoire(base.ApiObject):
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
		return base.Price(self._data['value'], 'gold')
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.cost.currency

class Egg(base.ApiObject):
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
		return base.Price(self._data['value'], 'gems')
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.price.currency

class HatchingPotion(base.ApiObject):
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
		return base.Price(self._data['value'], 'gems')
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.price.currency
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

class Food(base.ApiObject): # pragma: no cover -- FIXME no methods to retrieve yet.
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
		return base.Price(self._data['value'], 'gems')
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.price.currency

class Background(base.ApiObject):
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
		return base.Price(
				self._data['price'],
				self._data['currency'] if 'currency' in self._data else 'gems',
				)
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.price.currency
	@property
	def set_name(self):
		return self._data['set']

class HealthOverflowError(Exception):
	def __init__(self, hp, maxHealth):
		self.hp, self.maxHealth = hp, maxHealth
	def __str__(self):
		return 'HP is too high, part of health potion would be wasted.'

class HealthPotion(base.ApiObject):
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
		return base.Price(self._data['value'], 'gold')
	@property
	def currency(self): # pragma: no cover -- FIXME deprecated
		return self.cost.currency
	def _buy(self, user):
		if self.overflow_check and float(user.stats.hp) + self.VALUE > user.stats.maxHealth:
			raise HealthOverflowError(user.stats.hp, user.stats.maxHealth)
		user._data = self.api.post('user', 'buy-health-potion').data

class Pet(base.ApiObject):
	def __init__(self, _special=None, **kwargs):
		super().__init__(**kwargs)
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

class Mount(base.ApiObject):
	def __init__(self, _special=None, **kwargs):
		super().__init__(**kwargs)
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
