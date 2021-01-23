""" Quests: definitions and progress.
"""
from collections import namedtuple
from functools import lru_cache
from . import base
from .content import ContentEntry, MarketableForGems, parse_habitica_event

class Rage(base.ApiObject):
	# TODO 'desperation' ('stressbeat' world quest)
	def __init__(self, *args, _rage_progress=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._rage_progress = _rage_progress
	@property
	def value(self):
		return base.ValueBar(
				self._rage_progress if self._rage_progress is not None else self._data['value'],
				self._data['value'],
				)
	@property
	def effect(self):
		return self._data.get('effect')
	@property
	def description(self):
		return self._data['description']
	@property
	def stables(self):
		return self._data.get('stables')
	@property
	def bailey(self):
		return self._data.get('bailey')
	@property
	def guide(self):
		return self._data.get('guide')
	@property
	def tavern(self):
		return self._data.get('tavern')
	@property
	def quests(self):
		return self._data.get('quests')
	@property
	def seasonalShop(self):
		return self._data.get('seasonalShop')
	@property
	def market(self):
		return self._data.get('market')
	@property
	def title(self):
		return self._data['title']
	@property
	def healing(self):
		return self._data.get('healing')
	@property
	def mpDrain(self):
		return self._data.get('mpDrain')

class QuestBoss(base.ApiObject):
	def __init__(self, *args, _rage_progress=None, _hp_progress=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._rage_progress = _rage_progress
		self._hp_progress = _hp_progress
	@property
	def name(self):
		return self._data['name']
	@property
	def strength(self):
		return self._data['str']
	@property
	def defense(self):
		return self._data['def']
	@property
	def hp(self):
		return base.ValueBar(
				self._hp_progress if self._hp_progress is not None else self._data['hp'],
				self._data['hp'],
				)
	@property
	def rage(self):
		data = self._data.get('rage')
		return self.child(Rage, data, _rage_progress=self._rage_progress) if data else None

QuestCollectItem = namedtuple('QuestCollectItem', 'key text count')

class QuestCollect(base.ApiObject):
	def __init__(self, *args, _collect_progress=None, **kwargs):
		super().__init__(*args, **kwargs)
		self._collect_progress = _collect_progress
	@property
	def names(self):
		return list(self._data.keys())
	def get_item(self, key):
		data = self._data[key]
		return QuestCollectItem(key, data['text'], data['count'])
	def items(self):
		return [
				QuestCollectItem(
					key,
					self._data[key]['text'],
					base.ValueBar(
						self._collect_progress[key] if self._collect_progress is not None else self._data[key]['count'],
						self._data[key]['count'],
						),
					)
				for key in self._data
				]
	@property
	def current(self):
		value = sum(_ for _ in self._collect_progress.values()) if self._collect_progress is not None else 0
		return base.ValueBar(
				value,
				self.total,
				)
	@property
	def total(self):
		return sum(_['count'] for _ in self._data.values())

class QuestDropItem(base.ApiObject):
	def get_content_entry(self):
		return getattr(self.content, self._data['type'])(key=self._data['key'])
	@property
	def key(self):
		return self._data['key']
	@property
	def text(self):
		return self._data['text']
	@property
	def type(self):
		return self._data['type']
	@property
	def onlyOwner(self):
		return self._data.get('onlyOwner', False)

class QuestDrop(base.ApiObject):
	@property
	def unlock(self):
		return self._data.get('unlock', '')
	@property
	def experience(self):
		return self._data['exp']
	@property
	def gold(self):
		return base.Price(self._data['gp'], 'gold')
	@property
	def items(self):
		return self.children(QuestDropItem, self._data.get('items', []))

class QuestUnlockCondition(base.ApiObject):
	@property
	def text(self):
		return self._data['text']
	@property
	def condition(self):
		return self._data['condition']
	@property
	def incentiveThreshold(self):
		return self._data['incentiveThreshold']

class LazyQuestData:
	def __init__(self, quest_key, _content=None):
		self.content = _content
		self.key = quest_key
		self._data = None
	def _ensure(self):
		if self._data is None:
			self._data = self.content['quests'][self.key]
	def __getitem__(self, key):
		self._ensure()
		return self._data[key]
	def get(self, key, default=None):
		self._ensure()
		return self._data.get(key, default)

class Quest(ContentEntry, MarketableForGems):
	def __init__(self, *args, _content=None, _data=None, _group_progress=None, _user_progress=None, **kwargs):
		if _data is None:
			assert _group_progress or _user_progress
			if _group_progress:
				quest_key = _group_progress['key']
			elif _user_progress:
				quest_key = _user_progress['key']
			else: # pragma: no cover
				raise RuntimeError('Expected either quest data, or group progress, or user progress, received nothing at all.')
			_data = LazyQuestData(quest_key, _content=_content)
		super().__init__(*args, _content=_content, _data=_data, **kwargs)
		self._group_progress = _group_progress
		self._user_progress = _user_progress
	@property
	def title(self):
		return self.text
	@property
	def userCanOwn(self):
		return self.category in self.content.userCanOwnQuestCategories
	@property
	def category(self):
		return self._data['category']
	@property
	def level(self):
		return self._data.get('lvl')
	@property
	def unlockCondition(self):
		data = self._data.get('unlockCondition')
		return self.child(QuestUnlockCondition, data) if data else None
	@property
	def goldValue(self):
		return base.Price(self._data['goldValue'], 'gold') if 'goldValue' in self._data else None
	@property
	def group(self):
		return self._data.get('group')
	@property
	def previous(self):
		key = self._data.get('previous')
		return self.content.get_quest(key) if key else None
	@property
	def completion(self):
		return self._data['completion']
	@property
	def completionChat(self):
		return self._data.get('completionChat')
	@property
	def boss(self):
		result = self._data.get('boss')
		rage_progress = self._group_progress.get('rage') if self._group_progress else None
		hp_progress = self._group_progress['progress']['hp'] if self._group_progress else None
		return self.child(QuestBoss, result, _rage_progress=rage_progress, _hp_progress=hp_progress) if result else None
	@property
	def collect(self):
		result = self._data.get('collect')
		collect_progress = self._group_progress['progress']['collect'] if self._group_progress else None
		return self.child(QuestCollect, result, _collect_progress=collect_progress) if result else None
	@property
	def drop(self):
		return self.child(QuestDrop, self._data['drop'])
	@property
	def colors(self):
		return self._data.get('colors', dict())
	@property
	def event(self):
		if 'event' not in self._data:
			return None
		return parse_habitica_event(self._data['event'])
	# Group progress (/group/.quest):
	# TODO .extra
	# TODO .members
	def _get_group(self):
		from . import groups
		if not self._group_progress or not isinstance(self._parent, groups.Group):
			raise RuntimeError('Quest is not linked to a group!')
		return self._parent
	@property
	def active(self):
		if not self._group_progress:
			if not self._user_progress:
				return False
			return True # Considering quest active if user has pending progress.
		return bool(self._group_progress['active'])
	def leader(self):
		if not self._group_progress:
			return None
		from . import user
		return self.child(user.Member, self.api.get('members', self._group_progress['leader']).data)
	def abort(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'abort').data
		self._group_progress.update(data)
	def accept(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'accept').data
		self._group_progress.update(data)
	def cancel(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'cancel').data
		self._group_progress.update(data)
	def force_start(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'force-start').data
		self._group_progress.update(data)
	def leave(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'leave').data
		self._group_progress.update(data)
	def reject(self):
		data = self.api.post('groups', self._get_group().id, 'quests', 'reject').data
		self._group_progress.update(data)
	# User progress (/user/.party.quest):
	@property
	def up(self): # TODO is it pending damage to the boss by user?
		return self._user_progress['progress']['up'] if self._user_progress else 0
	@property
	def down(self): # TODO is it pending damage to the user?
		return self._user_progress['progress']['down'] if self._user_progress else 0
	@property
	def collected(self): # FIXME is it dict of pending items to be collected?
		return self._user_progress['progress']['collect'] if self._user_progress else None
	@property
	def collectedItems(self): # TODO what is it?
		return self._user_progress['progress']['collectedItems'] if self._user_progress else None
	@property
	def completed(self): # FIXME is it an ID?
		return self._user_progress['completed'] if self._user_progress else None
	@property
	def RSVPNeeded(self):
		return self._user_progress['RSVPNeeded'] if self._user_progress else False
	def _buy(self, user):
		if self.goldValue:
			return self.api.post('user', 'buy-quest', self.key)
		return self.api.post('user', 'purchase', 'quests', self.key)
