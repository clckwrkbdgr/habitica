from .. import api
from . import base, content, tasks, groups, user
from .content import *
from .groups import *
from .tasks import *
from .user import *
from .user import UserProxy

# TODO the whole /debug/ route for development

class Coupon(base.ApiObject):
	# TODO get/ and generate/ - require sudo permissions.
	@property
	def code(self):
		return self._data
	def validate(self):
		return self.api.post('coupons', 'validate', self._data).valid
	def _buy(self, user):
		user._data = self.api.post('coupons', 'enter', self._data).data

class Habitica(base.ApiInterface):
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
	def coupon(self, code):
		return self.child(Coupon, code)
	def run_cron(self):
		self.api.post('cron')

	@property
	def user(self):
		""" Returns current user: `habitica.user()`
		May be used as direct proxy to user task list without redundant user() call:
			habitica.user.habits()
			habitica.user.rewards()
		"""
		return self.child_interface(UserProxy)
	def groups(self, *group_types):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		result = self.api.get('groups', type=','.join(group_types)).data
		# TODO recognize party and return Party object instead.
		return self.children(Group, result)
