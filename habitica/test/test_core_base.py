import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
from ..core import base

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
