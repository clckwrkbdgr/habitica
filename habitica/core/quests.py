""" Quests: definitions and progress.
"""
from collections import namedtuple
from functools import lru_cache
from . import base
from .content import ContentEntry, MarketableForGems, parse_habitica_event

class Rage(base.ApiObject):
	# TODO 'desperation' ('stressbeat' world quest)
	@property
	def value(self):
		return self._data['value']
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
		return self._data['hp']
	@property
	def rage(self):
		data = self._data.get('rage')
		return self.child(Rage, data) if data else None

QuestCollectItem = namedtuple('QuestCollectItem', 'key text count')

class QuestCollect(base.ApiObject):
	@property
	def names(self):
		return list(self._data.keys())
	def get_item(self, key):
		data = self._data[key]
		return QuestCollectItem(key, data['text'], data['count'])
	def items(self):
		return [
				QuestCollectItem(key, self._data[key]['text'], self._data[key]['count'])
				for key in self._data
				]
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

class Quest(ContentEntry, MarketableForGems):
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
		return self.child(QuestBoss, result) if result else None
	@property
	def collect(self):
		result = self._data.get('collect')
		return self.child(QuestCollect, result) if result else None
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

class QuestProgress(base.ApiObject):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self._quest_definition = self.content.quests(self._data['key'])
	@property
	@lru_cache()
	def quest(self):
		return self._quest_definition
	@property
	def active(self):
		return bool(self._data['active'])
	@property
	def title(self):
		return self.text
	@property
	def progress(self):
		if self.quest.collect:
			qp_tmp = self._data['progress']['collect']
			quest_progress = sum(qp_tmp.values())
			return base.ValueBar(quest_progress, self.quest.collect.total)
		else:
			return base.ValueBar(self._data['progress']['hp'], self.quest.boss.hp)
	@property
	def max_progress(self): # pragma: no cover -- FIXME deprecated
		return self.progress.max_value
	def __getattr__(self, attr):
		return getattr(self.quest, attr)
