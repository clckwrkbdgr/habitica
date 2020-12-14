""" Base definitions for other modules.
Mostly non-functional.
"""

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
