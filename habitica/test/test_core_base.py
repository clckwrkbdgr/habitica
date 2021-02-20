import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
from ..core import base
from ..api import dotdict

class TestUtils(unittest.TestCase):
	def should_get_text_repr_of_a_number(self):
		self.assertEqual(base.textsign(-1), '-')
		self.assertEqual(base.textsign(100), '+')
		self.assertEqual(base.textsign(0), '')
		self.assertEqual(base.signed(0.1234), '+0.123')
		self.assertEqual(base.signed(-1234.56789, 5), '-1234.56789')
	def should_update_dict_recursively(self):
		original = {
				'topvalue' : 'foo',
				'untouched' : 'foo',
				'toplevel' : {
					'subvalue' : 'bar',
					'untouched' : 'bar',
					'sublevel' : {
						},
					},
				'dotdict' : dotdict({'key':'value', 'untouched':'value'}),
				'nested' : { 'nested' : { 'nested' : {
					'untouched' : 'baz',
					'nested' : { 'nested' : {
						'bottom' : 'baz',
						},
						}, },
					}, },
				}
		new_values = {
				'topvalue' : 'new foo',
				'toplevel' : {
					'subvalue' : 'new bar',
					'sublevel' : {
						'key' : 'value',
						},
					'new sublevel' : {
						'another key' : 'another value',
						},
					},
				'dotdict' : {
					'key' : 'new value',
					},
				'nested' : { 'nested' : { 'nested' : {
					'nested' : { 'nested' : {
						'bottom' : 'new baz',
						},
						}, },
					}, },
				}

		base.update_dict_deep(original, new_values)

		self.assertEqual(set(original.keys()), {'topvalue', 'untouched', 'toplevel', 'dotdict', 'nested'})
		self.assertEqual(original['topvalue'], 'new foo')
		self.assertEqual(original['untouched'], 'foo')
		self.assertEqual(set(original['toplevel'].keys()), {'subvalue', 'untouched', 'sublevel', 'new sublevel'})
		self.assertEqual(original['toplevel']['subvalue'], 'new bar')
		self.assertEqual(original['toplevel']['untouched'], 'bar')
		self.assertEqual(original['toplevel']['sublevel'], {'key':'value'})
		self.assertEqual(original['toplevel']['new sublevel'], {'another key':'another value'})
		self.assertEqual(set(original['dotdict'].keys()), {'key', 'untouched'})
		self.assertEqual(original['dotdict'].key, 'new value')
		self.assertEqual(original['dotdict'].untouched, 'value')
		self.assertEqual(original['nested'], {
			'nested' : { 'nested' : {
				'untouched' : 'baz',
				'nested' : { 'nested' : {
					'bottom' : 'new baz',
					},
					}, },
				},
			})

class MockApiObject(base.ApiObject):
	pass

class MockApiInterface(base.ApiInterface):
	pass

class MockChildApiObject(base.ApiObject):
	pass

class MockChildApiInterface(base.ApiInterface):
	pass

class MockAnyObject:
	pass

class TestApiObject(unittest.TestCase):
	def should_create_api_object_as_child(self):
		obj = MockApiObject(_data={'foo':'bar'}, _api='API', _parent=self, _content='CONTENT')
		child = obj.child(MockChildApiObject, {'subfoo':'subbar'})
		self.assertEqual(type(child), MockChildApiObject)
		self.assertEqual(child._data, {'subfoo':'subbar'})
		self.assertEqual(child.api, 'API')
		self.assertEqual(child.content, 'CONTENT')
		self.assertEqual(id(child._parent), id(obj))
	def should_create_api_interface_as_child(self):
		obj = MockApiObject(_api='API', _parent=self, _content='CONTENT')
		child = obj.child_interface(MockChildApiInterface)
		self.assertEqual(type(child), MockChildApiInterface)
		self.assertEqual(child.api, 'API')
		self.assertEqual(child.content, 'CONTENT')
		self.assertEqual(id(child._parent), id(obj))
	def should_create_children_only_as_api_object_subclasses(self):
		obj = MockApiObject(_data={'foo':'bar'}, _api='API', _parent=self, _content='CONTENT')
		with self.assertRaises(ValueError):
			obj.child(MockAnyObject, {'subfoo':'subbar'})
		intrf = MockApiInterface(_api='API', _parent=self, _content='CONTENT')
		with self.assertRaises(ValueError):
			intrf.child_interface(MockAnyObject)
	def should_create_multiple_api_objects_as_children(self):
		obj = MockApiObject(_data={'foo':'bar'}, _api='API', _parent=self, _content='CONTENT')
		children = obj.children(MockChildApiObject, ['first', 'second'])
		self.assertEqual(len(children), 2)
		child = children[0]
		self.assertEqual(type(child), MockChildApiObject)
		self.assertEqual(child._data, 'first')
		self.assertEqual(child.api, 'API')
		self.assertEqual(child.content, 'CONTENT')
		self.assertEqual(id(child._parent), id(obj))
		child = children[1]
		self.assertEqual(type(child), MockChildApiObject)
		self.assertEqual(child._data, 'second')
		self.assertEqual(child.api, 'API')
		self.assertEqual(child.content, 'CONTENT')
		self.assertEqual(id(child._parent), id(obj))

class TestValueBar(unittest.TestCase):
	def should_return_string_representation(self):
		value = base.ValueBar(10.5, 50)
		self.assertEqual(str(value), '10.5/50')
		self.assertEqual(repr(value), 'ValueBar(10.5, 50)')
	def should_return_value_when_casted_to_int(self):
		value = base.ValueBar(10.5, 50)
		self.assertEqual(int(value), 10)
	def should_return_value_when_casted_to_float(self):
		value = base.ValueBar(10.5, 50)
		self.assertEqual(float(value), 10.5)
	def should_return_max_value_via_max_builtine(self):
		value = base.ValueBar(10.5, 50)
		self.assertEqual(max(value), 50)
	def should_recognize_empty_bar(self):
		value = base.ValueBar(10.5, 50)
		self.assertTrue(value)
		value = base.ValueBar(0, 50)
		self.assertFalse(value)
	def should_add_or_substract_value(self):
		value = base.ValueBar(10.5, 50)

		value += 1
		self.assertEqual(float(value), 11.5)
		value = value + 1
		self.assertEqual(float(value), 12.5)
		value = 1 + value
		self.assertEqual(float(value), 13.5)

		value -= 1
		self.assertEqual(float(value), 12.5)
		value = value - 1
		self.assertEqual(float(value), 11.5)
		value = 22 - value
		self.assertEqual(float(value), 10.5)
	def should_keep_value_within_bar_boundaries(self):
		value = base.ValueBar(150, 50)
		self.assertEqual(float(value), 50)
		value = base.ValueBar(-150, 50)
		self.assertEqual(float(value), 0)
		value += 150
		self.assertEqual(float(value), 50)
		value = value - 150
		self.assertEqual(float(value), 0)

		value.value = 100500
		self.assertEqual(float(value), 50)
		value.value = -100500
		self.assertEqual(value, 0)
	def should_compare_bar_with_numbers(self):
		value = base.ValueBar(10.5, 50)
		self.assertTrue(value < 25)
		self.assertTrue(value > 5)
		self.assertEqual(value, 10.5)
		self.assertNotEqual(value, 10.1)

class TestPrice(unittest.TestCase):
	def should_return_string_representation(self):
		value = base.Price(10.5, 'gems')
		self.assertEqual(str(value), '10.5 gems')
		self.assertEqual(repr(value), "Price(10.5, 'gems')")
	def should_return_value_when_casted_to_int(self):
		value = base.Price(10.5, 'gems')
		self.assertEqual(int(value), 10)
	def should_return_value_when_casted_to_float(self):
		value = base.Price(10.5, 'gems')
		self.assertEqual(float(value), 10.5)
	def should_recognize_empty_price(self):
		value = base.Price(10.5, 'gems')
		self.assertTrue(value)
		value = base.Price(0, 'gems')
		self.assertFalse(value)
	def should_perform_arithmetic_operations(self):
		price = base.Price(10.5, 'gems')
		gem = base.Price(1, 'gems')
		self.assertEqual((price + 1).value, 11.5)
		self.assertEqual((price + gem).value, 11.5)
		self.assertEqual((1 + price).value, 11.5)
		self.assertEqual((gem + price).value, 11.5)
		self.assertEqual((price - 1).value, 9.5)
		self.assertEqual((price - gem).value, 9.5)
		self.assertEqual((21 - price).value, 10.5)
		self.assertEqual((price * 2).value, 21)
		self.assertEqual((2 * price).value, 21)
		self.assertAlmostEqual((price / 2).value, 5.25)
		self.assertAlmostEqual((price // 2).value, 5)
	def should_raise_on_operations_with_different_currencies(self):
		price = base.Price(10.5, 'gems')
		bad = base.Price(1, 'gold')
		with self.assertRaises(ValueError):
			new_price = base.Price(price, 'gold')
		with self.assertRaises(ValueError):
			price + bad
		with self.assertRaises(ValueError):
			bad + price
		with self.assertRaises(ValueError):
			price - bad
		with self.assertRaises(ValueError):
			bad - price
		with self.assertRaises(ValueError):
			price * bad
		with self.assertRaises(ValueError):
			bad * price
		with self.assertRaises(ValueError):
			price / bad
		with self.assertRaises(ValueError):
			price // bad
	def should_compare_price_with_numbers(self):
		value = base.Price(10.5, 50)
		self.assertTrue(value < 25)
		self.assertTrue(value > 5)
		self.assertEqual(value, 10.5)
		self.assertNotEqual(value, 10.1)
