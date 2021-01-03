from . import base

class Tag(base.Entity):
	@property
	def name(self):
		return self._data['name']
	@property
	def is_challenge(self):
		return self._data.get('challenge', False)
	def group(self):
		if not self._data.get('group'):
			return None
		from . import groups
		return self.child(groups.Group, self.api.get('groups', self._data['group']).data)
	def rename(self, name):
		self._data = self.api.put('tags', self.id, _body={
			'name' : name,
			}).data
	def delete(self):
		self.api.delete('tags', self.id)
		self._data = None
	def move_to(self, position):
		self.api.post('reorder-tags', _body={
			'tagId' : self.id,
			'to' : int(position),
			})
