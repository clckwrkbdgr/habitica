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
