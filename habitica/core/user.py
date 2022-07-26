""" User and user-related functionality: inventory, spells etc.
"""
from . import base, content, tasks, groups, tags
from ..api import dotdict

class UserAppearance(base.ApiObject):
	# TODO unlock hair.color.* etc
	@property
	def size(self):
		return self._data['size']
	@property
	def hair_color(self):
		return self._data['hair']['color']
	@property
	def hair_base(self):
		return self._data['hair']['base']
	@property
	def hair_bangs(self):
		return self._data['hair']['bangs']
	@property
	def hair_beard(self):
		return self._data['hair']['beard']
	@property
	def hair_mustache(self):
		return self._data['hair']['mustache']
	@property
	def hair_flower(self):
		return self._data['hair']['flower']
	@property
	def skin(self):
		return self._data['skin']
	@property
	def shirt(self):
		return self._data['shirt']
	@property
	def sound(self):
		return self._data['sound']
	@property
	def chair(self):
		return self._data['chair']

class UserPreferences(base.ApiObject):
	# TODO .webhooks
	# TODO .emailNotifications
	# TODO .pushNotifications
	# TODO .suppressModals
	# TODO .tasks - ??
	@property
	def appearance(self):
		return self.child(UserAppearance, self._data)
	@property
	def dayStart(self):
		return self._data['dayStart']
	@property
	def timezoneOffset(self):
		return self._data['timezoneOffset']
	@property
	def timezoneOffsetAtLastCron(self):
		return self._data['timezoneOffsetAtLastCron']
	@property
	def hideHeader(self):
		return self._data['hideHeader']
	@property
	def language(self):
		return self._data['language']
	@property
	def automaticAllocation(self):
		return self._data['automaticAllocation']
	@property
	def allocationMode(self):
		return self._data['allocationMode']
	@property
	def autoEquip(self):
		return self._data['autoEquip']
	@property
	def costume(self):
		return self._data['costume']
	@property
	def dateFormat(self):
		return self._data['dateFormat']
	@property
	def sleep(self):
		return self._data['sleep']
	@property
	def stickyHeader(self):
		return self._data['stickyHeader']
	@property
	def disableClasses(self):
		return self._data['disableClasses']
	@property
	def newTaskEdit(self):
		return self._data['newTaskEdit']
	@property
	def dailyDueDefaultView(self):
		return self._data['dailyDueDefaultView']
	@property
	def advancedCollapsed(self):
		return self._data['advancedCollapsed']
	@property
	def toolbarCollapsed(self):
		return self._data['toolbarCollapsed']
	@property
	def reverseChatOrder(self):
		return self._data['reverseChatOrder']
	@property
	def background(self):
		return self._data['background']
	@property
	def displayInviteToPartyWhenPartyIs1(self):
		return self._data['displayInviteToPartyWhenPartyIs1']
	@property
	def improvementCategories(self):
		return self._data['improvementCategories']
	def set_custom_day_start(self, dayStart):
		self.api.post('user', 'custom-day-start', _body={'dayStart':dayStart})
		self._data['dayStart'] = dayStart

class Buffs(base.ApiObject, content.BaseStats):
	@property
	def stealth(self):
		return self._data['stealth']
	@property
	def streaks(self):
		return self._data['streaks']
	@property
	def snowball(self):
		return self._data['snowball']
	@property
	def spookySparkles(self):
		return self._data['spookySparkles']
	@property
	def shinySeeds(self):
		return self._data['shinySeeds']
	@property
	def seafoam(self):
		return self._data['seafoam']

class Training(base.ApiObject, content.BaseStats):
	pass

class UserStats(base.ApiObject, content.BaseStats):
	# TODO .points - ???
	def _handle_events(self):
		self._track_stat('class')
		self._track_stat('gp')
	@property
	def class_name(self):
		return self._data['class']
	@property
	def hp(self):
		return base.ValueBar(self._data['hp'], self._data['maxHealth'])
	@property
	def maxHealth(self): # pragma: no cover -- FIXME deprecated
		return self.hp.max_value
	@property
	def level(self):
		return self._data['lvl']
	@property
	def experience(self):
		return base.ValueBar(self._data['exp'],
				self._data['exp'] + self._data['toNextLevel'],
				)
	@property
	def maxExperience(self): # pragma: no cover -- FIXME deprecated
		return self.experience.max_value
	@property
	def mana(self):
		return base.ValueBar(self._data['mp'], self._data['maxMP'])
	@property
	def maxMana(self): # pragma: no cover -- FIXME deprecated
		return self.mana.max_value
	@property
	def gold(self):
		return self._data['gp']
	@property
	def buffs(self):
		return self.child(Buffs, self._data['buffs'])
	@property
	def training(self):
		return self.child(Training, self._data['training'])
	def allocate(self, strength=None, intelligence=None, perception=None, constitution=None):
		stats = {}
		if strength:
			stats['str'] = strength
		if intelligence:
			stats['int'] = intelligence
		if perception:
			stats['per'] = perception
		if constitution:
			stats['con'] = constitution
		assert stats, "No stat was specified to allocate"
		if len(stats) == 1 and next(iter(stats.values())) == 1:
			data = self.api.post('user', 'allocate', stat=next(iter(stats.keys()))).data
		else:
			data = self.api.post('user', 'allocate-bulk', _body={'stats':stats}).data
		self._handle_events()
		self._update(data)
	def autoallocate_all(self):
		data = self.api.post('user', 'allocate-now').data
		self._handle_events()
		self._update(data)

class Gear(base.ApiObject):
	@property
	def weapon(self):
		return self.content.gear(self._data['weapon'])
	@property
	def armor(self):
		return self.content.gear(self._data['armor'])
	@property
	def head(self):
		return self.content.gear(self._data['head'])
	@property
	def shield(self):
		return self.content.gear(self._data['shield'])
	@property
	def back(self):
		return self.content.gear(self._data['back'])
	@property
	def headAccessory(self):
		return self.content.gear(self._data['headAccessory'])
	@property
	def eyewear(self):
		return self.content.gear(self._data['eyewear'])
	@property
	def body(self):
		return self.content.gear(self._data['body'])

class Inventory(base.ApiObject):
	# TOOD items.special -- see User model.
	@property
	def lastDrop(self):
		""" {.date, .count} """
		return dotdict(self._data['lastDrop'])
	@property
	def food(self):
		return [
				base.ItemBundle(self.content.food(key), amount)
				for key, amount
				in self._data['food'].items()
				]
	@property
	def pet(self):
		return self.content.petInfo(self._data['currentPet']) if self._data['currentPet'] else None
	@property
	def mount(self):
		return self.content.mountInfo(self._data['currentMount']) if self._data.get('currentMount') else None
	@property
	def eggs(self):
		return self._data['eggs'] # FIXME is it a dict of IDs?
	@property
	def hatchingPotions(self):
		return self._data['hatchingPotions'] # FIXME is it a dict of IDs?
	@property
	def pets(self):
		return self._data['pets'] # FIXME is it a dict of IDs?
	@property
	def mounts(self):
		return self._data['mounts'] # FIXME is it a dict of IDs?
	@property
	def quests(self):
		return self._data['quests'] # FIXME is it a dict of IDs?
	@property
	def gear(self):
		return self._data['gear']['owned'] # FIXME is it a dict of IDs?
	@property
	def costume(self):
		return self.child(Gear, self._data['gear']['costume'])
	@property
	def equipped(self):
		return self.child(Gear, self._data['gear']['equipped'])

class _UserMethods:
	""" Trait to be used by ApiObject or ApiInterface
	to access user methods that do not require user data.
	"""
	def party(self):
		""" Returns user's party. """
		return self.child(groups.Party, self.api.get('groups', 'party').data)
	def group_plans(self):
		return self.children(groups.Group, self.api.get('group-plans').data)
	def join(self, group):
		group._data = self.api.post('groups', group.id, 'join').data
	def leave(self, group, keep_tasks=True, leave_challenges=True):
		self.api.post('groups', group.id, 'leave', keep='keep-all' if keep_tasks else 'remove-all', _body={
			'keepChallenges' : 'leave-challenges' if leave_challenges else 'remain-in-challenges'
			})
	def reject_invite(self, group):
		self.api.post('groups', group.id, 'reject-invite').data

	def habits(self):
		return self.children(tasks.Habit, self.api.get('tasks', 'user', type='habits').data)
	def dailies(self, dueDate=None):
		query = {
				'type' : 'dailys',
				}
		if dueDate: # pragma: no cover -- TODO requires real testing first.
			query['dueDate'] = dueDate # FIXME convert to what format?
		return self.children(tasks.Daily, self.api.get('tasks', 'user', **query).data)
	def todos(self):
		return self.children(tasks.Todo, self.api.get('tasks', 'user', type='todos').data)
	def rewards(self):
		return self.children(tasks.Reward, self.api.get('tasks', 'user', type='rewards').data)
	def create_task(self, task_obj):
		data = self.api.post('tasks', 'user', _body=task_obj._data).data
		return self.child(tasks.Task.type_from_str(data['type']), data)
	def challenges(self, page=0):
		return self.children(groups.Challenge, self.api.get('challenges', 'user', member=True, page=page).data)
	def tags(self):
		return self.children(tags.Tag, self.api.get('tags').data)
	def clearCompletedTodos(self):
		self.api.post('tasks', 'clearCompletedTodos')

class UserProxy(base.ApiInterface, _UserMethods):
	""" Lazy class to proxy call methods that do not require immediate user data,
	like lists of tasks, challenges, user's party etc:
	   habitica.user.todos()
	   habitica.user.party()
	   ...
	To get real User out of this proxy, call this object like a method:
	   real_user = habitica.user()
	   real_user.todos()
	   real_user.party()
	   ...
	"""
	def __call__(self):
		# TODO supports query userFields=...,...
		return self.child(User, self.api.get('user').data, _parent=self._parent)

class Email:
	""" External person: only e-mail and optional name.
	Used mostly for invites.
	"""
	def __init__(self, email, name=None):
		self.email = email
		self.name = name

class Achievement(base.ApiObject):
	@property
	def label(self):
		return self._parent._data['label']
	@property
	def title(self):
		return self._data['title']
	@property
	def text(self):
		return self._data['text']
	@property
	def icon(self):
		# TODO returns icon name. Should return icon object/file.
		return self._data['icon']
	@property
	def earned(self):
		return self._data['earned']
	@property
	def index(self):
		return self._data['index']
	@property
	def value(self):
		return self._data['value']
	@property
	def optionalCount(self):
		return self._data['optionalCount']

class Achievements(base.ApiObject):
	@property
	def label(self):
		return self._data['label']
	@property
	def achievements(self):
		return self.children(Achievement, self._data['achievements'].values())
	def __len__(self):
		return len(self._data['achievements'])
	def __iter__(self):
		return iter(self.achievements)

class Member(base.Entity):
	""" All other Habitica users beside you. """
	@property
	def name(self):
		return self._data.get('profile', {}).get('name')
	@property
	def preferences(self):
		return self._data.get('preferences', {})
	@property
	def inbox(self):
		return self._data.get('inbox', {})
	@property
	def stats(self):
		return self._data.get('stats', {})
	@property
	def items(self):
		return self._data.get('items', {})
	def achievements(self):
		""" Returns dict {label:Achivements()} """
		achievements = self._data.get('achievements')
		if not achievements:
			achievements = self.api.get('members', self.id, 'achievements').data
			self._data['achievements'] = achievements
		return dotdict({label:self.child(Achievements, entries) for label, entries in achievements.items()})
	@property
	def auth(self):
		return self._data.get('auth', {})
	def party(self):
		return self.child(groups.Party, self._data.get('party', {}))
	def tasks(self):
		return self.children(tasks.Task, self._data.get('tasks', []))

class User(base.Entity, _UserMethods):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.stats._handle_events()
	# TODO auth -- see model
	# TODO achievements -- see model
	# TODO backer -- see model
	# TODO contributor -- see model
	# TODO purchased -- see model
	# TODO history -- see model
	# TODO challenges -- see model
	# TODO invitations -- see model
	# TODO newMessages -- see model
	# TODO notifications -- see model
	# TODO tags -- see model
	# TODO inbox -- see model; POST user/mark-pms-read
	# TODO POST move-pinned-item
	# TODO extra -- see model
	# TODO pushDevices -- see model
	# TODO webhooks -- see model
	# TODO pinnedItems, pinnedItemsOrder, unpinnedItems -- see model
	# TODO POST toggle-pinned-item
	# TODO party.order, party.orderAscending -- see model
	# TODO PUT /user
	# TODO POST /user/unequip/:type
	@property
	def name(self):
		return self._data['profile']['name']
	@property
	def imageUrl(self):
		return self._data['profile']['imageUrl']
	@property
	def blurb(self):
		return self._data['profile']['blurb']
	@property
	def quest(self):
		from . import quests
		return self.child(quests.Quest, None, _user_progress=self._data['party']['quest'])
	@property
	def stats(self):
		return self.child(UserStats, self._data['stats'])
	@property
	def flags(self):
		# See User model (GET /models/user/paths)
		# TODO useful flags:
        # "flags.dropsEnabled": "Boolean",
        # "flags.itemsEnabled": "Boolean",
        # "flags.lastNewStuffRead": "String",
        # "flags.rewrite": "Boolean",
        # "flags.classSelected": "Boolean",
        # "flags.mathUpdates": "Boolean",
        # "flags.rebirthEnabled": "Boolean",
        # "flags.lastFreeRebirth": "Date",
        # "flags.levelDrops": "Mixed",
        # "flags.chatRevoked": "Boolean",
        # "flags.chatShadowMuted": "Boolean",
        # "flags.lastWeeklyRecap": "Date",
        # "flags.lastWeeklyRecapDiscriminator": "Boolean",
        # "flags.cronCount": "Number",
        # "flags.welcomed": "Boolean",
        # "flags.armoireEnabled": "Boolean",
        # "flags.armoireOpened": "Boolean",
        # "flags.armoireEmpty": "Boolean",
        # "flags.cardReceived": "Boolean",
        # "flags.warnedLowHealth": "Boolean",
		return dotdict(self._data['flags'])
	@property
	def preferences(self):
		return self.child(UserPreferences, self._data['preferences'])
	@property
	def inventory(self):
		return self.child(Inventory, self._data['items'])
	@property
	def balance(self):
		return base.Price(self._data['balance'], 'gems')
	@property
	def loginIncentives(self):
		return self._data['loginIncentives']
	@property
	def invitesSent(self):
		return self._data['invitesSent']
	@property
	def needsCron(self):
		return self._data['needsCron']
	@property
	def lastCron(self):
		return self._data['lastCron'] # FIXME parse date
	@property
	def gemsLeft(self):
		plan = self._data.purchased.get('plan')
		if not plan:
			return 0
		planGemLimits_convCap = 25 # TODO hardcoded in Habitica itself.
		return planGemLimits_convCap + plan['consecutive']['gemCapExtra'] - plan['gemsBought']
	def notifications(self):
		data = self._data['notifications']
		from . import Notifications
		return self.child(Notifications, data)
	def avatar(self):
		""" Returns pure HTML code to render user avatar.
		Behavior may change in the future.
		"""
		# TODO Rendering avatar as PNG is broken for years.
		# TODO There are also other (private) methods on /export/ route.
		# TODO Render as image and cache.
		return self.api.get('export', 'avatar-{0}.html'.format(self.id), _as_json=False)
	def buy(self, item):
		if not isinstance(item, base.Marketable):
			raise RuntimeError("Item is not Marketable, cannot be bought: {0}".format(type(item)))
		item.buy(user=self)
	def sell(self, item, amount=None):
		if not isinstance(item, base.Sellable):
			raise RuntimeError("Item is not Sellable, cannot be sold: {0}".format(type(item)))
		item.sell(user=self, amount=amount)
	def spells(self):
		""" Returns list of available spells. """
		available_spells = self.content.spells(self.stats.class_name)
		available_spells = [spell for spell in available_spells if self.stats.level >= spell.lvl]
		return available_spells
	def get_spell(self, spell_key):
		""" Returns spell by its spell key if available to the user, otherwise None. """
		return self.content.get_spell(self.stats.class_name, spell_key)
	def cast(self, spell, target=None):
		if not isinstance(spell, content.Castable):
			raise RuntimeError("Object cannot is not castable: {0}".format(type(spell)))
		params = {}
		if target:
			params = {'targetId' : target.id}
		result = self.api.post('user', 'class', 'cast', spell.key, **params).data
		if 'user' in result:
			self._update(result['user'])
			del result['user']
		if 'task' in result and isinstance(target, tasks.Task):
			target._update(result['task'])
			del result['task']
		return result
	def change_class(self, new_class):
		self._update(self.api.post('user', 'change-class', **({'class':new_class})).data)
	def disable_classes(self):
		self._update(self.api.post('user', 'disable-classes').data)
	def wear_costume(self, item):
		if not isinstance(item, content.Gear):
			raise RuntimeError("Can wear only Gear as costume, not {0}".format(type(item)))
		self._update(self.api.post('user', 'equip', 'costume', item.key).data)
	def equip_gear(self, item):
		if not isinstance(item, content.Gear):
			raise RuntimeError("Can equip only Gear, not {0}".format(type(item)))
		self._update(self.api.post('user', 'equip', 'equipped', item.key).data)
	def select_pet(self, pet):
		if not isinstance(pet, content.Pet):
			raise RuntimeError("Can select only Pet as a pet, not {0}".format(type(pet)))
		self._update(self.api.post('user', 'equip', 'pet', pet.key).data)
	def ride_mount(self, mount):
		if not isinstance(mount, content.Mount):
			raise RuntimeError("Can ride only Mount, not {0}".format(type(mount)))
		self._update(self.api.post('user', 'equip', 'mount', mount.key).data)
	def hatch_pet(self, egg, potion):
		self._update(self.api.post('user', 'hatch', egg.key, potion.key).data)
	def sleep(self):
		if self.preferences.sleep:
			return
		self._data['preferences']['sleep'] = self.api.post('user', 'sleep').data
	def wake_up(self):
		if not self.preferences.sleep:
			return
		self._data['preferences']['sleep'] = self.api.post('user', 'sleep').data
	def read_card(self, card):
		self._update(self.api.post('user', 'read-card', card.key).data)
	def revive(self):
		self._update(self.api.post('user', 'revive').data)
