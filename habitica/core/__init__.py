from .. import api
from . import base, content, tasks, groups, user, quests, tags
from .content import *
from .groups import *
from .tasks import *
from .user import *
from .tags import *
from .quests import *
from .user import UserProxy

# TODO the whole /debug/ route for development

class Coupon(base.ApiObject, base.Marketable):
	# TODO get/ and generate/ - require sudo permissions.
	@property
	def code(self):
		return self._data
	def validate(self):
		return self.api.post('coupons', 'validate', self._data).valid
	def _buy(self, user):
		return self.api.post('coupons', 'enter', self._data)

class Message(base.ApiObject):
	def delete(self): # pragma: no cover -- TODO
		# TODO apparently returns user.inbox.messages
		return self.api.delete('user', 'messages', self.id).data

class NewsPost(base.ApiObject):
	@property
	def title(self):
		return self._data['title']
	@property
	def text(self):
		return self._data['text']
	@property
	def credits(self):
		return self._data['credits']
	@property
	def author(self):
		return self.child(Member, self.api.get('members', self._data['author']).data)
	@property
	def publishDate(self):
		return self._data['publishDate'] # FIXME parse date
	@property
	def published(self):
		return self._data['published']

class News(base.ApiObject):
	# TODO create a new news post (POST /news/)
	# TODO delete a news post (DELETE /news/)
	# TODO update a news post (PUT /news/)
	@property
	def html_text(self):
		return self._data
	def mark_as_read(self):
		self.api.post('news', 'read')
	def tell_me_later(self):
		self.api.post('news', 'tell-me-later')

class StableKey(base.ApiInterface, base.MarketableForGems):
	def __init__(self, _api=None, _content=None, _parent=None, _method=None, _value=None):
		super().__init__(_api=_api, _content=_content, _parent=_parent)
		self._method = _method
		self._data = {
				'value' : _value,
				}
	def _buy(self, user):
		# TODO returns message (to display)
		return self.api.post('user', self._method)

class FortifyPotion(base.ApiInterface, base.MarketableForGems):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._data = {
				'value' : 4,
				}
	def _buy(self, user):
		# TODO returns message (to display)
		return self.api.post('user', 'reroll')

class OrbOfRebirth(base.ApiInterface, base.MarketableForGems):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._data = {
				'value' : 6, # TODO free if level >= 100, but needs user data for that.
				}
	def _buy(self, user):
		# TODO returns message (to display)
		return self.api.post('user', 'rebirth')

class Market(base.ApiObject):
	def gear(self):
		if 'gear' not in self._data:
			self._data['gear'] = self.children(content.Gear, self.api.get('user', 'inventory', 'buy').data)
		return self._data['gear']
	def rewards(self):
		""" Returns in-app rewards (gear etc). """
		if 'rewards' not in self._data:
			self._data['rewards'] = self.children(content.Gear, self.api.get('user', 'in-app-rewards').data)
		return self._data['rewards']
	def open_mystery_item(self):
		# TODO also returns message (to display)
		return self.child(content.Gear, self.api.post('user', 'open-mystery-item').data)
	@property
	def key_to_the_kennels(self):
		return self.child_interface(StableKey, _method='release-mounts', _value=4)
	@property
	def master_key_to_the_kennels(self):
		return self.child_interface(StableKey, _method='release-both', _value=6) # TODO free after all pets+mounts are collected - need to check User inventory for that.
	@property
	def fortify_potion(self):
		return self.child_interface(FortifyPotion)
	@property
	def orb_of_rebirth(self):
		return self.child_interface(OrbOfRebirth)

class Habitica(base.ApiInterface):
	""" Main Habitica entry point. """
	# TODO /hall/{heroes,patrons}
	# TODO /user/block
	# TODO DELETE /user
	# TODO DELETE /user/auth/social/:network
	# TODO GET /user/anonymized
	# TODO POST /user/auth/local/register
	# TODO POST /user/reset-password
	# TODO POST /user/reset
	# TODO PUT /user/auth/update-email
	# TODO PUT /user/auth/update-password
	# TODO PUT /user/auth/update-username
	# TODO webhooks
	def __init__(self, auth=None, _api=None):
		# TODO POST /user/auth/local/login
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
	def groups(self, *group_types, paginate=False, page=0):
		""" Returns list of groups of given types.
		Supported types are: PARTY, GUILDS, PRIVATE_GUILDS, PUBLIC_GUILDS, TAVERN
		"""
		if paginate or page:
			result = self.api.get('groups', type=','.join(group_types), paginate="true", page=page).data
		else:
			result = self.api.get('groups', type=','.join(group_types)).data
		# TODO recognize party and return Party object instead.
		return self.children(groups.Group, result)
	def market(self):
		return self.child(Market, {})
	def tavern(self):
		return self.child(Group, self.api.get('groups', 'habitrpg').data)
	def create_plan(self):
		result = self.api.post('groups', 'create-plan').data
		return self.child(Group, result)
	def create_guild(self, name, public=False):
		result = self.api.post('groups', _body={
			'name' : name,
			'type' : 'guild',
			'public' : 'public' if public else 'private',
			}).data
		return self.child(Group, result)
	def create_party(self, name):
		result = self.api.post('groups', _body={
			'name' : name,
			'type' : 'party',
			'public' : 'private',
			}).data
		return self.child(Party, result)
	def inbox(self, page=None, conversation=None):
		params = {}
		if page:
			params['page'] = page
		if conversation: # pragma: no cover -- TODO
			params['conversation'] = conversation.id
		return self.children(Message, self.api.get('inbox', 'messages', **params).data)
	def clear_inbox(self): # pragma: no cover -- TODO
		""" Deletes all inbox messages. """
		self.api.delete('user', 'messages')
	def member(self, id):
		return self.child(user.Member, self.api.get('members', id).data)
	def transfer_gems(self, member, gems, message):
		gems = base.Price(gems, 'gems')
		objections = self.api.get('members', member.id, 'objections', 'transfer-gems').data
		if objections:
			raise RuntimeError(objections)
		self.api.post('members', 'transfer-gems', _body={
			'toUserId' : member.id,
			'gemAmount' : gems.value,
			'message' : message,
			})
	def send_private_message(self, member, message):
		objections = self.api.get('members', member.id, 'objections', 'send-private-message').data
		if objections:
			raise RuntimeError(objections)
		return self.child(Message, self.api.post('members', 'send-private-message', _body={
			'toUserId' : member.id,
			'message' : message,
			}).data)
	def news(self, post_id=None):
		if post_id:
			return self.child(NewsPost, self.api.get('news', post_id).data)
		html_data = self.api.get('news').data
		return self.child(News, html_data)
	def create_tag(self, name):
		return self.child(Tag, self.api.post('tags', _body={
			'name' : name,
			}).data)
	def _get_tag(self, tag_id):
		return self.child(Tag, self.api.get('tags', tag_id).data)
