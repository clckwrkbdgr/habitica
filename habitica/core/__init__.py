from .. import api
from . import base, content, tasks, groups, user
from .content import *
from .groups import *
from .tasks import *
from .user import *
from .user import _UserProxy

class Habitica:
	""" Main Habitica entry point. """
	def __init__(self, auth=None, _api=None):
		self.api = _api or api.API(auth['url'], auth['x-api-user'], auth['x-api-key'])
		self._content = None
	def home_url(self):
		""" Returns main Habitica Web URL to open in browser. """
		return self.api.base_url + '/#/tasks'
	def server_is_up(self):
		""" Retruns True if main Habitica service is available. """
		server = self.api.get('status').data
		return server.status == 'up'
	@property
	def content(self):
		if self._content is None:
			self._content = Content(_api=self.api)
		return self._content

	@property
	def user(self):
		""" Returns current user: `habitica.user()`
		May be used as direct proxy to user task list without redundant user() call:
			habitica.user.habits()
			habitica.user.rewards()
		"""
		return _UserProxy(_api=self.api, _content=self.content)
	def groups(self, *group_types):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		result = self.api.get('groups', type=','.join(group_types)).data
		# TODO recognize party and return Party object instead.
		return [Group(_data=entry, _api=self.api) for entry in result]
