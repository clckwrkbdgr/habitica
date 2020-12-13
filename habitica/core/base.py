""" Base definitions for other modules.
Mostly non-functional.
"""

class ApiObject:
	""" Base class for all objects that:
	- has immediate parent (._parent);
	- holds data (._data);
	- has access to main Habitica's Content() object (.content);
	- can communicate with server via API (.api).
	"""
	def __init__(self, _api=None, _data=None, _content=None, _parent=None):
		self.api = _api
		self._data = _data
		self._parent = _parent
		self.content = _content
	def child(self, obj_type, data, _parent=None):
		""" Creates ApiObject from given data
		and passes through API, Content and parent (self).
		If _parent is specified, it overrides value of 'self'.
		"""
		if obj_type is not ApiObject and not issubclass(obj_type, ApiObject):
			raise ValueError('Expected subclass of base.ApiObject, got instead: {0}'.format(obj_type))
		return obj_type(_data=data, _api=self.api, _content=self.content, _parent=(_parent or self))
	def children(self, obj_type, data_entries, _parent=None):
		""" Returns list of ApiObjects from given sequence of data (each entry for each object)
		and passes through API, Content and parent (self).
		"""
		return [self.child(obj_type, entry) for entry in data_entries]
