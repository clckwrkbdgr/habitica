""" Base definitions for other modules.
Mostly non-functional.
"""
import functools
import vintage

class ApiInterface:
	""" Base class for all objects that:
	- has immediate parent (._parent);
	- has access to main Habitica's Content() object (.content);
	- can communicate with server via API (.api).
	I.e. just interface to API without real data.
	"""
	def __init__(self, _api=None, _content=None, _parent=None):
		self.api = _api
		self.content = _content
		self._parent = _parent
	def child_interface(self, obj_type, _parent=None, **params):
		""" Creates ApiInterface (without data)
		and passes through API, Content and parent (self).
		If _parent is specified, it overrides value of 'self'.
		"""
		if obj_type is not ApiInterface and not issubclass(obj_type, ApiInterface):
			raise ValueError('Expected subclass of base.ApiInterface, got instead: {0}'.format(obj_type))
		return obj_type(_api=self.api, _content=self.content, _parent=(_parent or self), **params)
	def child(self, obj_type, data, _parent=None, **params):
		""" Creates ApiObject from given data
		and passes through API, Content and parent (self).
		If _parent is specified, it overrides value of 'self'.
		"""
		if obj_type is not ApiObject and not issubclass(obj_type, ApiObject):
			raise ValueError('Expected subclass of base.ApiObject, got instead: {0}'.format(obj_type))
		return obj_type(_data=data, _api=self.api, _content=self.content, _parent=(_parent or self), **params)
	def children(self, obj_type, data_entries, _parent=None, **params):
		""" Returns list of ApiObjects from given sequence of data (each entry for each object)
		and passes through API, Content and parent (self).
		"""
		return [self.child(obj_type, entry, _parent=_parent, **params) for entry in data_entries]

class ApiObject(ApiInterface):
	""" Base class for all objects that:
	- are PureApiObject;
	- holds data (._data);
	I.e. any kind of Habitica data entity.
	"""
	def __init__(self, _api=None, _data=None, _content=None, _parent=None):
		super().__init__(_api=_api, _content=_content, _parent=_parent)
		self._data = _data

class Entity(ApiObject):
	""" Base class for all API objects that have ID.
	Supports property .id
	Recognizes both data fields 'id' and '_id'.
	"""
	@property
	def id(self):
		result = self._data.get('_id')
		if result:
			return result
		return self._data.get('id', None)

@functools.total_ordering
class ValueBar:
	""" Represents value (int or float) bounded by 0 and some maximum value.
	Value can be retrieved via bar.value, int(bar), float(bar).
	Max value can be retrieved via bar.max_value or max(bar).
	Supports direct arithmetic operations with numbers: +, -.
	Resulting value cannot go out of bounds (0, max_value)
	and will be reset to the coressponding bound value.
	"""
	def __init__(self, value, max_value):
		self.value = max(0, min(value, max_value))
		self.max_value = max_value
	def _validate(self):
		if self.value < 0:
			self.value = 0
		elif self.value > self.max_value:
			self.value = self.max_value
	def __str__(self):
		return '{0}/{1}'.format(self.value, self.max_value)
	def __repr__(self):
		return 'ValueBar({0}, {1})'.format(repr(self.value), repr(self.max_value))
	def __bool__(self):
		return bool(self.value)
	def __int__(self):
		self._validate()
		return int(self.value)
	def __float__(self):
		self._validate()
		return float(self.value)
	def __iter__(self):
		self._validate()
		return iter( (self.max_value,) )
	def __add__(self, other):
		return ValueBar(self.value + other, self.max_value)
	def __radd__(self, other):
		return ValueBar(other + self.value, self.max_value)
	def __sub__(self, other):
		return ValueBar(self.value - other, self.max_value)
	def __rsub__(self, other):
		return ValueBar(other - self.value, self.max_value)
	def __lt__(self, other):
		self._validate()
		return self.value < other
	def __eq__(self, other):
		self._validate()
		return self.value == other

@functools.total_ordering
class Price:
	""" Represents price (value with currency).
	Value can be retrieved via bar.value, int(bar), float(bar).
	Currency can be retrieved via bar.currency.
	Supports all arithmetic operations and casting to numbers (int, float).
	"""
	def __init__(self, value, currency):
		if isinstance(value, Price) and value.currency != currency:
			raise ValueError('Cannot convert {0} into {1}'.format(repr(value), repr(currency)))
		self.value = value
		self.currency = currency
	def __str__(self):
		return '{0} {1}'.format(self.value, self.currency)
	def __repr__(self):
		return 'Price({0}, {1})'.format(repr(self.value), repr(self.currency))
	def __bool__(self):
		return bool(self.value)
	def __int__(self):
		return int(self.value)
	def __float__(self):
		return float(self.value)
	def _ensure_same_currency(self, other):
		if isinstance(other, Price) and other.currency != self.currency:
			raise ValueError('Cannot perform operations on different currency: expected {0}, got instead: {1}'.format(repr(self.currency), repr(other.currency)))
	def __add__(self, other):
		self._ensure_same_currency(other)
		return Price(self.value + other, self.currency)
	def __radd__(self, other):
		self._ensure_same_currency(other)
		return Price(other + self.value, self.currency)
	def __sub__(self, other):
		self._ensure_same_currency(other)
		return Price(self.value - other, self.currency)
	def __rsub__(self, other):
		self._ensure_same_currency(other)
		return Price(other - self.value, self.currency)
	def __mul__(self, other):
		self._ensure_same_currency(other)
		return Price(self.value * other, self.currency)
	def __rmul__(self, other):
		self._ensure_same_currency(other)
		return Price(other * self.value, self.currency)
	def __truediv__(self, other):
		self._ensure_same_currency(other)
		return Price(self.value / other, self.currency)
	def __floordiv__(self, other):
		self._ensure_same_currency(other)
		return Price(self.value // other, self.currency)
	def __lt__(self, other):
		self._ensure_same_currency(other)
		return self.value < other
	def __eq__(self, other):
		self._ensure_same_currency(other)
		return self.value == other

class Marketable:
	""" Mixin for objects that can be bought (at market, from time travellers etc).
	Supports both properties .cost and .price (return the same Price object).
	Searches for 'value', 'cost', 'price' in object's data.
	If there is no specific currency in data, searches for a class field .CURRENCY.
	See alse MarketableFor<CurrencyType> descendants.

	Supports method buy(<user>), which allows user object to .buy(item).
	"""
	CURRENCY = NotImplemented
	@property
	def cost(self):
		return Price(
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
	def buy(self, user):
		""" Allows User object to buy purchasable items via user.buy(...)
		May alter User's data upon purchase.

		Each implementation method ._buy(user) should return _full_ response (with .data and .message)
		or None if no update or notification is needed.
		"""
		# TODO gold check?
		response = self._buy(user)
		if response:
			# TODO also returns .message (to display)
			user._data.update(response.data)
	def _buy(self, user): # pragma: no cover
		raise NotImplementedError

class MarketableForGold(Marketable):
	CURRENCY = 'gold'

class MarketableForGems(Marketable):
	CURRENCY = 'gems'

class Sellable:
	""" Mixin for objects that can be sold at market for gold (potions, eggs, food).
	Supports method sell(user[, amount]) which allows user object to .buy(item[, amount])
	"""
	def sell(self, user, amount=None):
		""" Allows User object to sell items via user.sell(...)
		May alter User's data upon selling.

		Each implementation method ._sell(user) should return _full_ response (with .data and .message)
		or None if no update or notification is needed.
		"""
		# TODO gold check?
		response = self._sell(user, amount=amount)
		if response:
			# TODO also returns .message (to display)
			user._data.update(response.data)
	def _sell(self, user, amount=None): # pragma: no cover
		raise NotImplementedError
