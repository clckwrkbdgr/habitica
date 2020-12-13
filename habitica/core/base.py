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
