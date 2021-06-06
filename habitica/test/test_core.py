import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
import datetime
import copy
from collections import namedtuple
from .. import core, api, timeutils
from ..core.base import Price
from .mock_api import MockAPI, MockRequest, MockDataRequest, MockData

class TestBaseHabitica(unittest.TestCase):
	def should_get_home_url(self):
		habitica = core.Habitica(_api=MockAPI())
		self.assertEqual(habitica.home_url(), 'http://localhost/#/tasks')
	def should_detect_working_server(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['status'], {'data': {'status': 'up'}}),
			MockRequest('get', ['status'], {'data': {'status': ''}}),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertFalse(habitica.server_is_up())
	def should_retrieve_and_cache_content(self):
		habitica = core.Habitica(_api=MockAPI(
			))
		content = habitica.content
		content.my_value = 'foo'
		content = habitica.content
		self.assertEqual(content.my_value, 'foo')
	def should_get_user_proxy_without_calls(self):
		habitica = core.Habitica(_api=MockAPI(
			))
		user = habitica.user
	def should_get_user_directly_via_proxy(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			))
		user = habitica.user()
	def should_get_groups(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			))
		groups = habitica.groups(core.Group.PARTY, core.Group.GUILDS)
		self.assertEqual(len(groups), 5)
		group = next(_ for _ in groups if _.type == 'party')
		self.assertEqual(group.name, 'Denton brothers')
		self.assertEqual(group.type, 'party')
		self.assertEqual(group.privacy, 'private')
	def should_paginate_list_of_groups(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS[:1]),
			))
		groups = habitica.groups(core.Group.PARTY, core.Group.GUILDS, page=1)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0].name, 'Illuminati')
		self.assertEqual(groups[0].type, 'guild')
		self.assertEqual(groups[0].privacy, 'private')
	def should_run_cron(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('post', ['cron'], {}),
			))
		habitica.run_cron()
	def should_get_tavern(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups', 'habitrpg'], MockData.GROUPS['tavern']),
			))
		group = habitica.tavern()
		self.assertEqual(group.name, 'Tavern')
		self.assertEqual(group.type, 'habitrpg')
	def should_get_inbox_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['inbox', 'messages'], {'data':
				[
					],
				}),
			))
		group = habitica.inbox(page=1)
	def should_get_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			))
		member = habitica.member('pauldenton')
		self.assertEqual(member.name, 'Paul Denton')
		self.assertEqual(member.party().id, 'party')
		self.assertEqual(member.inbox, {'not':'explained'})
		self.assertEqual(member.preferences, {'not':'explained'})
		self.assertEqual(member.stats, {'not':'explained'})
		self.assertEqual(member.items, {'not':'explained'})
		self.assertEqual(list(member.achievements().basic)[0].title, 'Sign Up')
		self.assertEqual(member.auth, {'not':'explained'})
	def should_transfer_gems_to_a_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockRequest('get', ['members', 'pauldenton', 'objections', 'transfer-gems'], {'data': [
				{'not':'explained'},
				]}),
			MockRequest('get', ['members', 'pauldenton', 'objections', 'transfer-gems'], {'data': [
				]}),
			MockRequest('post', ['members', 'transfer-gems'], {'data': [ ]}),
			))
		member = habitica.member('pauldenton')
		with self.assertRaises(RuntimeError):
			habitica.transfer_gems(member, Price(1, 'gems'), 'Here you go.')
		habitica.transfer_gems(member, Price(1, 'gems'), 'Here you go.')
	def should_send_private_message_to_a_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['members', 'pauldenton'], {'data': {
				'_id' : 'pauldenton',
				}}),
			MockRequest('get', ['members', 'pauldenton', 'objections', 'send-private-message'], {'data': [
				{'not':'explained'},
				]}),
			MockRequest('get', ['members', 'pauldenton', 'objections', 'send-private-message'], {'data': [
				]}),
			MockRequest('post', ['members', 'send-private-message'], {'data': {
				'not':'explained',
				}}),
			))
		member = habitica.member('pauldenton')
		with self.assertRaises(RuntimeError):
			habitica.send_private_message(member, 'Incoming message.')
		message = habitica.send_private_message(member, 'Incoming message.')
		self.assertEqual(message._data, {'not':'explained'})
	def should_get_market_items(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user', 'inventory', 'buy'], sorted(MockData.CONTENT_DATA['gear']['flat'].values(), key=lambda _:_['key'])),
			MockDataRequest('get', ['user', 'in-app-rewards'], sorted(MockData.CONTENT_DATA['gear']['flat'].values(), key=lambda _:_['key'])[2:]),
			MockDataRequest('post', ['user', 'open-mystery-item'], MockData.CONTENT_DATA['gear']['flat']['mysterykatana']),
			))
		market = habitica.market()
		gear = market.gear()
		self.assertEqual(gear[1].key, 'dragonstooth')
		gear = market.gear()
		self.assertEqual(gear[1].key, 'dragonstooth')

		gear = market.rewards()
		self.assertEqual(gear[0].key, 'mysterykatana')

		gear = market.open_mystery_item()
		self.assertEqual(gear.key, 'mysterykatana')

class TestNotifications(unittest.TestCase):
	def _response_with_notification(self, type=None, seen=False, _id=None, **data):
		return MockRequest('get', ['status'], {
			'data': {'status': 'up'},
			'notifications' : [
				{
					'id' : _id or 'notification-1',
					'type' : type,
					'data' : data,
					'seen' : seen,
					},
				],
			})
	def should_ignore_seen_notifications(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='NEW_CHAT_MESSAGE', seen=True, group={'name':'UNATCO'}),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			])
	def should_ignore_previously_captured_notifications(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='NEW_CHAT_MESSAGE', group={'name':'UNATCO'}, _id='msg1'),
			self._response_with_notification(type='NEW_CHAT_MESSAGE', group={'name':'UNATCO'}, _id='msg1'),
			MockDataRequest('post', ['notifications', 'see'], []),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'Group "UNATCO" have new message',
			])
		habitica.mark_all_notifications_as_seen()
	def should_detect_unknown_notifications(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='UNKNOWN', key='value'),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			"Unknown notification UNKNOWN. Data: {'key': 'value'}",
			])

	def should_catch_cron_notification(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='CRON', _id='1', hp=-1, mp=3.1415),
			self._response_with_notification(type='CRON', _id='2', hp=-1),
			self._response_with_notification(type='CRON', _id='3', mp=3.1415),
			self._response_with_notification(type='CRON', _id='4', hp=0, mp=0),
			))
		for _ in range(4):
			self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'Cron: HP -1, Mana +3.142',
			'Cron: HP -1',
			'Cron: Mana +3.142',
			'Cron!',
			])
	def should_catch_unallocated_stat_points(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='UNALLOCATED_STATS_POINTS', points=3, _id='first'),
			self._response_with_notification(type='UNALLOCATED_STATS_POINTS', points=21, _id='second'),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'You have 3 unallocated stat points',
			])
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'You have 21 unallocated stat point',
			])
	def should_catch_new_message(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='NEW_CHAT_MESSAGE', group={'name':'UNATCO'}),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'Group "UNATCO" have new message',
			])
	def should_catch_messages_in_responses(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockRequest('post', ['user', 'rebirth'], {
				'data' : MockData.USER,
				'message' : "You've restarted your adventure!",
				}),
			))
		user = habitica.user()
		orb = habitica.market().orb_of_rebirth
		user.buy(orb)
		self.assertEqual(list(map(str, habitica.events.dump())), [
			"You've restarted your adventure!",
			])
	def should_catch_achievements(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='ACHIEVEMENT_BONE_COLLECTOR', modalText='You collected all the Skeleton Pets!', achievement='boneCollector', message='Achievement! Bone Collector'),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'Achievement! Bone Collector: You collected all the Skeleton Pets!',
			])
	def should_catch_streak_achievement(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='STREAK_ACHIEVEMENT'),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'Streak achievement!',
			])
	def should_catch_mystery_items(self):
		habitica = core.Habitica(_api=MockAPI(
			self._response_with_notification(type='NEW_MYSTERY_ITEMS', items=['armor_mystery_202103', 'head_mystery_202103']),
			))
		self.assertTrue(habitica.server_is_up())
		self.assertEqual(list(map(str, habitica.events.dump())), [
			'New 2 mystery items!',
			])

class TestChallenges(unittest.TestCase):
	def _challenge(self, path=('groups', 'unatco')):
		return MockDataRequest('get', ['challenges'] + list(path), MockData.ORDERED.CHALLENGES)
	def should_fetch_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['members', 'manderley'], MockData.MEMBERS['manderley']),
			MockDataRequest('get', ['tasks', 'augments'], MockData.REWARDS['augments']),
			MockDataRequest('get', ['tasks', 'liberty'], MockData.TODOS['liberty']),
			MockDataRequest('get', ['tasks', 'armory'], MockData.DAILIES['armory']),
			MockDataRequest('get', ['tasks', 'carryon'], MockData.HABITS['carryon']),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		self.assertEqual(challenge.id, 'unatco')
		self.assertEqual(challenge.name, 'UNATCO missions')
		self.assertEqual(challenge.shortName, 'UNATCO')
		self.assertEqual(challenge.summary, 'Missions for UNATCO')
		self.assertEqual(challenge.description, 'Perform missions for UNATCO')
		self.assertEqual(challenge.createdAt, 1600000000)
		self.assertEqual(challenge.updatedAt, 1600000000)
		self.assertEqual(challenge.prize, 4)
		self.assertEqual(challenge.memberCount, 2)
		self.assertFalse(challenge.official)
		self.assertEqual(challenge.leader().id, 'manderley')

		group = challenge.group()
		self.assertEqual(group.id, party.id)
		self.assertEqual(group.name, party.name)

		rewards = challenge.rewards()
		self.assertEqual(rewards[0].text, 'Use augmentation canister')
		todos = challenge.todos()
		self.assertEqual(todos[0].text, 'Free Liberty statue and resque agent.')
		dailies = challenge.dailies()
		self.assertEqual(dailies[0].text, 'Restock at armory')
		habits = challenge.habits()
		self.assertEqual(habits[0].text, 'Carry on, agent')
	def should_fetch_user_challenges(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			self._challenge(path=('user',)),
			MockDataRequest('get', ['members', 'manderley'], MockData.MEMBERS['manderley']),
			))
		user = habitica.user()
		challenge = user.challenges()[2]
		self.assertEqual(challenge.id, 'unatco')
		self.assertEqual(challenge.name, 'UNATCO missions')
		self.assertEqual(challenge.leader().id, 'manderley')
	def should_get_challenge_data_as_csv(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockRequest('get', ['challenges', 'unatco', 'export', 'csv'], 'AS CSV'),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		self.assertEqual(challenge.as_csv(), 'AS CSV')
	def should_create_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['challenges'], MockData.CHALLENGES['nsf']),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		challenge = party.create_challenge(
				'Create Habitica API tool', 'HabiticaAPI',
				summary='You have to create Habitica API tool',
				description='You have to create Habitica API tool',
				prize=4,
				)
		self.assertEqual(challenge.id, 'nsf')
	def should_clone_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockRequest('post', ['challenges', 'unatco', 'clone'], {'challenge': MockData.CHALLENGES['unatco']})
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		challenge = challenge.clone()
		self.assertEqual(challenge.id, 'unatco')
		self.assertEqual(challenge.name, 'UNATCO missions')
		self.assertEqual(challenge.shortName, 'UNATCO')
	def should_update_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('put', ['challenges', 'unatco'],
				dict(MockData.CHALLENGES['unatco'],
					name='Escape UNATCO',
					shortName='EscapeUNATCO',
					summary='Break off all contacts and links with UNATCO',
					),
				)
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		challenge.update()
		self.assertEqual(challenge.name, 'UNATCO missions')
		self.assertEqual(challenge.shortName, 'UNATCO')
		self.assertEqual(challenge.summary, 'Missions for UNATCO')
		challenge.update(
				name = 'Escape UNATCO',
				summary = 'EscapeUNATCO',
				description = 'Break off all contacts and links with UNATCO',
				)
		self.assertEqual(challenge.name, 'Escape UNATCO')
		self.assertEqual(challenge.shortName, 'EscapeUNATCO')
		self.assertEqual(challenge.summary, 'Break off all contacts and links with UNATCO')
	def should_join_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['challenges', 'unatco', 'join'], dict(MockData.CHALLENGES['unatco'], memberCount=3)),
			MockDataRequest('post', ['challenges', 'unatco', 'leave'], {}),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		challenge.join()
		self.assertEqual(challenge.memberCount, 3)
		challenge.leave()
		self.assertEqual(challenge.api.responses[-1].path[-1], 'leave')
	def should_select_winner(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['challenges', 'unatco', 'selectWinner', 'pauldenton'], {}),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		Person = namedtuple('Person', 'id name')
		challenge.selectWinner(Person('pauldenton', 'Name'))
		self.assertEqual(challenge.api.responses[-1].path[-2:], ['selectWinner', 'pauldenton'])
	def should_delete_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('delete', ['challenges', 'unatco'], {}),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		challenge.delete()
		self.assertEqual(challenge.api.responses[-1].method, 'delete')
		self.assertEqual(challenge.api.responses[-1].path[-1], 'unatco')
	def should_get_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['challenges', 'unatco', 'members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		member = challenge.member('pauldenton')
		self.assertEqual(member.id, 'pauldenton')
		self.assertEqual(member.name, 'Paul Denton')
		tasks = member.tasks()
		self.assertEqual(tasks[0].id, 'manderley')
		self.assertEqual(tasks[0].text, 'Manderley')
		self.assertEqual(tasks[0].notes, 'Visit Manderley for new missions')
	def should_get_members_for_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['challenges', 'unatco', 'members'], [
				MockData.MEMBERS['mj12trooper{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['challenges', 'unatco', 'members'], [
				MockData.MEMBERS['mj12trooper31']
				]),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		members = list(challenge.members())
		self.assertEqual(members[0].id, 'mj12trooper1')
		self.assertEqual(members[30].id, 'mj12trooper31')
	def should_create_task_for_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['tasks', 'challenge', 'unatco'], MockData.TODOS['liberty']),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		task = core.tasks.Todo(
				text='Free Liberty statue and resque agent.',
				alias='liberty statue',
				attribute='per',
				collapseChecklist=True,
				priority=core.tasks.Task.Priority.MEDIUM,
				reminders={'not':'explained'},
				tags=[],
				date=datetime.date(2016, 6, 20),
				)
		task = challenge.create_task(task)
		self.assertEqual(task.id, 'liberty')
	def should_unlink_all_tasks_from_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['tasks', 'unlink-all', 'unatco'], {}),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')
		challenge = party.challenges()[2]
		challenge.unlink_tasks(keep=False)

class TestChat(unittest.TestCase):
	def should_fetch_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'chat'], MockData.PARTY_CHAT),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		messages = party.chat()
		self.assertEqual(messages[0].id, 'chat1')
		self.assertEqual(messages[0].timestamp, 1600000000)
		self.assertEqual(messages[0].user, 'jcdenton')
		self.assertEqual(messages[0].text, 'Hello Paul')
		self.assertEqual(messages[1].id, 'chat2')
		self.assertEqual(messages[1].timestamp, 1600001000)
		self.assertEqual(messages[1].user, 'pauldenton')
		self.assertEqual(messages[1].text, 'Hello JC')
	def should_flag_message(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'chat'], MockData.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'party', 'chat', 'chat1', 'flag'], MockData.PARTY_CHAT_FLAGGED),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		message = party.chat()[0]
		message.flag(comment='Yazaban!')
		self.assertTrue(message._data['flagged'])
	def should_clear_message_from_flags(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'chat'], MockData.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'party', 'chat', 'chat1', 'clearflags'], {}),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		message = party.chat()[0]
		message.clearflags()
	def should_like_message(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'chat'], MockData.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'party', 'chat', 'chat1', 'like'], MockData.PARTY_CHAT_LIKED),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		message = party.chat()[0]
		message.like()
		self.assertEqual(message._data['liked'], 1)
	def should_mark_messages_as_read(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['groups', 'party', 'chat', 'seen'], {}),
			MockDataRequest('post', ['groups', 'party', 'chat', 'seen'], {}),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		party.chat.mark_as_read()
		party.mark_chat_as_read()
	def should_delete_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('delete', ['groups', 'party', 'chat', 'chat1'], {}),
			MockDataRequest('get', ['groups', 'party', 'chat'], [
				MockData.PARTY_CHAT[0]
				]),
			MockDataRequest('delete', ['groups', 'party', 'chat', 'chat1'], [
				MockData.PARTY_CHAT[1]
				]),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		chat = party.chat
		chat.delete(core.ChatMessage(_data={'id':'chat1'}))
		self.assertFalse(chat._entries)
		self.assertEqual(chat.messages()[0].id, 'chat1')
		self.assertEqual(chat.messages()[0].timestamp, 1600000000)
		self.assertEqual(chat.messages()[0].user, 'jcdenton')
		self.assertEqual(chat.messages()[0].text, 'Hello Paul')
		chat.delete(core.ChatMessage(_data={'id':'chat1'}))
		self.assertEqual(chat.messages()[0].id, 'chat2')
		self.assertEqual(chat.messages()[0].timestamp, 1600001000)
		self.assertEqual(chat.messages()[0].user, 'pauldenton')
		self.assertEqual(chat.messages()[0].text, 'Hello JC')
	def should_post_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['groups', 'party', 'chat'], [MockData.LONG_CHAT[0]]),
			MockDataRequest('get', ['groups', 'party', 'chat'], MockData.LONG_CHAT),
			MockDataRequest('post', ['groups', 'party', 'chat'], MockData.LONG_CHAT),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		chat = party.chat
		chat.post('I will have to kill you myself.')
		self.assertEqual(chat.messages()[0].id, 'chat5')
		self.assertEqual(chat.messages()[0].timestamp, 1600000000)
		self.assertEqual(chat.messages()[0].user, 'annanavarre')
		self.assertEqual(chat.messages()[0].text, 'I will have to kill you myself.')
		chat.post('Take your best shot, Flatlander Woman.')
		self.assertEqual(chat.messages()[2].id, 'chat7')
		self.assertEqual(chat.messages()[2].timestamp, 1600001000)
		self.assertEqual(chat.messages()[2].user, 'annanavarre')
		self.assertEqual(chat.messages()[2].text, 'How did you know--?')

class TestGroup(unittest.TestCase):
	def should_fetch_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['groups', 'party', 'add-manager'], {}),
			MockDataRequest('post', ['groups', 'party', 'remove-manager'], {}),
			))

		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		party.add_manager(core.Member(_data={'id':'pauldenton'}))
		party.remove_manager(core.Member(_data={'id':'pauldenton'}))
	def should_create_group_plan(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups', 'create-plan'], MockData.GROUPS['illuminati']),
			))
		group = habitica.create_plan()
		self.assertEqual(group.id, 'illuminati')
		self.assertEqual(group.name, 'Illuminati')
	def should_create_guild(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups'], MockData.GROUPS['nsf']),
			))
		group = habitica.create_guild('NSF', public=False)
		self.assertEqual(group.id, 'nsf')
		self.assertEqual(group.name, 'NSF')
		self.assertTrue(group.is_public)
	def should_create_party(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups'], MockData.GROUPS['party']),
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('get', ['tasks', 'augments'], MockData.REWARDS['augments']),
			MockDataRequest('get', ['tasks', 'liberty'], MockData.TODOS['liberty']),
			MockDataRequest('get', ['tasks', 'armory'], MockData.DAILIES['armory']),
			MockDataRequest('get', ['tasks', 'carryon'], MockData.HABITS['carryon']),
			))
		group = habitica.create_party('Denton brothers')
		self.assertTrue(type(group) is core.Party)
		self.assertEqual(group.id, 'party')
		self.assertEqual(group.name, 'Denton brothers')
		self.assertEqual(group.summary, 'Paul and JC')
		self.assertEqual(group.description, 'Coalition of Paul and JC Denton')
		self.assertFalse(group.is_public)
		self.assertTrue(group.bannedWordsAllowed)
		self.assertEqual(group.leaderOnly, {'challenges':True,'getGems':False})
		self.assertEqual(group.leader().id, 'pauldenton')
		self.assertEqual(group.memberCount, 1)
		self.assertEqual(group.challengeCount, 0)
		self.assertEqual(group.balance, Price(1, 'gems'))
		self.assertEqual(group.logo, 'deusex-logo')
		self.assertEqual(group.leaderMessage, 'Way to go')

		rewards = group.rewards()
		self.assertEqual(rewards[0].text, 'Use augmentation canister')
		todos = group.todos()
		self.assertEqual(todos[0].text, 'Free Liberty statue and resque agent.')
		dailies = group.dailies()
		self.assertEqual(dailies[0].text, 'Restock at armory')
		habits = group.habits()
		self.assertEqual(habits[0].text, 'Carry on, agent')
	def should_invite_users(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('post', ['groups', 'illuminati', 'invite'], {}),
			MockDataRequest('post', ['groups', 'illuminati', 'reject-invite'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		with self.assertRaises(ValueError):
			group.invite('neither Email nor Member')
		group.invite(
				core.Email('user@unatco.gov'),
				core.Email('another@unatco.gov', 'Some Agent'),
				habitica.member('pauldenton'),
				)

		habitica.user.reject_invite(group)
	def should_join_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['groups', 'illuminati', 'join'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		habitica.user.join(group)
	def should_leave_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['groups', 'illuminati', 'leave'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		habitica.user.leave(group, keep_tasks=False, leave_challenges=False)
	def should_remove_members_from_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('post', ['groups', 'unatco', 'removeMember', 'pauldenton'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[-1]
		member = habitica.member('pauldenton')
		group.removeMember(member)
	def should_get_invites_for_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'invites'], [
				MockData.MEMBERS['mj12trooper{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['groups', 'party', 'invites'], [
				MockData.MEMBERS['mj12trooper31'],
				]),
			))
		group = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id=='party')
		members = list(group.all_invites())
		self.assertEqual(members[0].id, 'mj12trooper1')
		self.assertEqual(members[30].id, 'mj12trooper31')
	def should_get_members_for_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('get', ['groups', 'party', 'members'], [
				MockData.MEMBERS['mj12trooper{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['groups', 'party', 'members'], [
				MockData.MEMBERS['mj12trooper31'],
				]),
			))
		group = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'party')
		members = list(group.members())
		self.assertEqual(members[0].id, 'mj12trooper1')
		self.assertEqual(members[30].id, 'mj12trooper31')
	def should_create_task_for_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.ORDERED.GROUPS),
			MockDataRequest('post', ['tasks', 'group', 'unatco'], MockData.DAILIES['manderley']),
			MockDataRequest('post', ['tasks', 'group', 'unatco'], MockData.DAILIES['medbay']),
			))
		party = next(_ for _ in habitica.groups(core.Group.GUILDS) if _.id == 'unatco')

		task = core.tasks.Daily(
				text='Manderley',
				notes='Visit Manderley for new missions',
				streak=0,
				frequency=core.tasks.DailyFrequency(
					startDate='2016-06-20T21:00:00.000Z',
					everyX=12,
					),
				)
		task = party.create_task(task)
		self.assertEqual(task.id, 'manderley')

		task = core.tasks.Daily(
				text='Visit medbay on Monday',
				streak=0,
				frequency=core.tasks.WeeklyFrequency(
					monday=True,
					tuesday=False,
					wednesday=False,
					thursday=False,
					friday=False,
					saturday=False,
					sunday=False,
					),
				)
		task = party.create_task(task)
		self.assertEqual(task.id, 'medbay')

class TestUser(unittest.TestCase):
	def _user_data(self, stats=None, **kwargs):
		result = dict(MockData.USER, **kwargs)
		result['stats'] = dict(result['stats'], **(stats or {}))
		return result
	def should_get_user_basic_info(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(user.name, 'JC Denton')
		self.assertEqual(user.blurb, 'not-explained')
		self.assertEqual(user.imageUrl, 'jcdenton-image')
		self.assertEqual(user.flags, {'not':'explained'})
		self.assertEqual(user.balance, Price(10, 'gems'))
		self.assertEqual(user.loginIncentives, 400)
		self.assertEqual(user.invitesSent, 2)
		self.assertEqual(user.lastCron, '2016-06-20T21:00:00.000Z')
		self.assertFalse(user.needsCron)
	def should_get_user_stats(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(user.stats.class_name, 'rogue')
		self.assertEqual(user.stats.hp, 30.0)
		self.assertEqual(user.stats.maxHealth, 50.0)
		self.assertEqual(user.stats.level, 33)
		self.assertEqual(user.stats.experience, 1049.4)
		self.assertEqual(user.stats.maxExperience, 1101.0)
		self.assertEqual(user.stats.mana, 11.0)
		self.assertEqual(user.stats.maxMana, 55.0)
		self.assertEqual(user.stats.gold, 15.0)

		self.assertEqual(user.stats.buffs.strength, 1)
		self.assertEqual(user.stats.buffs.intelligence, 2)
		self.assertEqual(user.stats.buffs.perception, 1)
		self.assertEqual(user.stats.buffs.constitution, 0)
		self.assertTrue(user.stats.buffs.stealth)
		self.assertTrue(user.stats.buffs.streaks)
		self.assertFalse(user.stats.buffs.snowball)
		self.assertFalse(user.stats.buffs.spookySparkles)
		self.assertFalse(user.stats.buffs.shinySeeds)
		self.assertFalse(user.stats.buffs.seafoam)

		self.assertEqual(user.stats.training.strength, 0)
		self.assertEqual(user.stats.training.intelligence, 1)
		self.assertEqual(user.stats.training.perception, 1)
		self.assertEqual(user.stats.training.constitution, 2)
	def should_get_user_appearance(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		appearance = user.preferences.appearance
		self.assertEqual(appearance.size, 1)
		self.assertEqual(appearance.hair_color, 2)
		self.assertEqual(appearance.hair_base, 3)
		self.assertEqual(appearance.hair_bangs, 4)
		self.assertEqual(appearance.hair_beard, 5)
		self.assertEqual(appearance.hair_mustache, 6)
		self.assertEqual(appearance.hair_flower, 7)
		self.assertEqual(appearance.skin, 8)
		self.assertEqual(appearance.shirt, 9)
		self.assertEqual(appearance.sound, 10)
		self.assertEqual(appearance.chair, 11)
	def should_get_user_preferences(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		prefs = user.preferences
		self.assertEqual(prefs.timezoneOffset, 180)
		self.assertEqual(prefs.timezoneOffsetAtLastCron, 180)
		self.assertEqual(prefs.dayStart, 180)
		self.assertTrue(prefs.hideHeader)
		self.assertEqual(prefs.language, 'en')
		self.assertFalse(prefs.automaticAllocation)
		self.assertEqual(prefs.allocationMode, 'not-explained')
		self.assertFalse(prefs.autoEquip)
		self.assertTrue(prefs.costume)
		self.assertEqual(prefs.dateFormat, 'not-explained')
		self.assertFalse(prefs.sleep)
		self.assertFalse(prefs.stickyHeader)
		self.assertFalse(prefs.disableClasses)
		self.assertFalse(prefs.newTaskEdit)
		self.assertFalse(prefs.dailyDueDefaultView)
		self.assertFalse(prefs.advancedCollapsed)
		self.assertFalse(prefs.toolbarCollapsed)
		self.assertFalse(prefs.reverseChatOrder)
		self.assertFalse(prefs.background)
		self.assertFalse(prefs.displayInviteToPartyWhenPartyIs1)
		self.assertFalse(prefs.improvementCategories)
	def should_set_custom_day_start(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'custom-day-start'], {}),
			))
		user = habitica.user()
		prefs = user.preferences
		prefs.set_custom_day_start(12)
		self.assertEqual(prefs.dayStart, 12)
	def should_get_user_inventory(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		inventory = user.inventory
		self.assertEqual(inventory.lastDrop, {
			'date' : 'not-explained',
			'count' : 'not-explained',
			})
		self.assertEqual(inventory.eggs, { 'not' : 'explained', })
		self.assertEqual(inventory.hatchingPotions, { 'not' : 'explained', })
		self.assertEqual(inventory.quests, { 'not' : 'explained', })
		self.assertEqual(inventory.pets, { 'not' : 'explained', })
		self.assertEqual(inventory.mounts, { 'not' : 'explained', })
		self.assertEqual(inventory.gear, { 'not' : 'explained', })
	def should_get_user_gear(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		gear = user.inventory.equipped
		self.assertEqual(gear.weapon.key, 'ninja_katana')
		self.assertEqual(gear.armor.key, 'Dummy')
		self.assertEqual(gear.head.key, 'Dummy')
		self.assertEqual(gear.shield.key, 'Dummy')
		self.assertEqual(gear.back.key, 'Dummy')
		self.assertEqual(gear.headAccessory.key, 'Dummy')
		self.assertEqual(gear.eyewear.key, 'Dummy')
		self.assertEqual(gear.body.key, 'Dummy')

		gear = user.inventory.costume
		self.assertEqual(gear.weapon.key, 'ninja_katana')
		self.assertEqual(gear.armor.key, 'Dummy')
		self.assertEqual(gear.head.key, 'Dummy')
		self.assertEqual(gear.shield.key, 'Dummy')
		self.assertEqual(gear.back.key, 'Dummy')
		self.assertEqual(gear.headAccessory.key, 'Dummy')
		self.assertEqual(gear.eyewear.key, 'Dummy')
		self.assertEqual(gear.body.key, 'Dummy')
	def should_get_food_in_user_inventory(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(len(user.inventory.food), 2)
		self.assertEqual(sum(_.amount for _ in user.inventory.food), 3)
	def should_get_user_pet_and_mount(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(user.inventory.pet.text, 'Fox')
		self.assertEqual(user.inventory.mount.text, 'Wolf')
	def should_buy_only_purchasable(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-health-potion'],
				self._user_data(stats={'hp':45.0}),
				),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.buy(habitica.content.premiumPets('fox'))
		user.buy(habitica.content.potion)
	def should_buy_health_potion(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-health-potion'],
				self._user_data(stats={'hp':45.0}),
				),
			))
		user = habitica.user()
		potion = habitica.content.potion
		user.buy(potion)
		self.assertEqual(user.stats.hp, 45.0)

		with self.assertRaises(core.HealthOverflowError) as e:
			potion = core.HealthPotion()
			user.buy(potion)
		self.assertEqual(str(e.exception), 'HP is too high, part of health potion would be wasted.')
	def should_validate_and_buy_coupon(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockRequest('post', ['coupons', 'validate', 'ABCD-1234'], {
				'valid': False,
				}),
			MockRequest('post', ['coupons', 'validate', '1234-ABCD'], {
				'valid': True,
				}),
			MockDataRequest('post', ['coupons', 'enter', '1234-ABCD'],
				self._user_data(stats={'gp':45.0}),
				),
			))

		user = habitica.user()

		coupon = habitica.coupon('ABCD-1234')
		self.assertEqual(coupon.code, 'ABCD-1234')
		self.assertFalse(coupon.validate())

		coupon = habitica.coupon('1234-ABCD')
		self.assertEqual(coupon.code, '1234-ABCD')
		self.assertTrue(coupon.validate())

		user.buy(coupon)
		self.assertEqual(user.stats.gold, 45.0)
	def should_buy_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-quest', 'laguardia1'],
				self._user_data(),
				),
			MockDataRequest('post', ['user', 'purchase', 'quests', 'area51'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.quests('laguardia1'))
		user.buy(habitica.content.quests('area51'))
	def should_buy_armoire_item(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-armoire'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.armoire)
	def should_buy_special_item(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-special-spell', 'congrats'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.special_items('congrats'))
	def should_buy_gems(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data(purchased={})),
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'purchase', 'gems', 'gem'],
				self._user_data(),
				),
			))

		user = habitica.user()
		self.assertEqual(user.gemsLeft, 0)

		user = habitica.user()
		self.assertEqual(user.gemsLeft, 47)
		user.buy(habitica.market().gems(user.gemsLeft))
	def should_buy_eggs_and_food(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'purchase', 'eggs', 'wolf'],
				self._user_data(),
				),
			MockDataRequest('post', ['user', 'purchase', 'food', 'Meat'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.eggs('wolf'))
		user.buy(habitica.content.food('Meat'))
	def should_buy_hatching_potions(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'purchase', 'hatchingPotions', 'base'],
				self._user_data(),
				),
			MockDataRequest('post', ['user', 'purchase', 'premiumHatchingPotions', 'shadow'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.hatchingPotions('base'))
		user.buy(habitica.content.premiumHatchingPotions('shadow'))
	def should_buy_gear(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-gear', 'ninja_katana'],
				self._user_data(),
				),
			MockDataRequest('post', ['user', 'purchase', 'gear', 'dragonstooth'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.gear('ninja_katana'))
		user.buy(habitica.content.gear('dragonstooth'))
	def should_buy_mystery_sets(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('post', ['user', 'buy-mystery-set', '202012'],
				self._user_data(),
				),
			))

		user = habitica.user()
		user.buy(habitica.content.mystery('202012'))
	def should_get_user_avatar(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockRequest('get', ['export', 'avatar-jcdenton.html'], '<html/>'),
			))

		user = habitica.user()
		self.assertEqual(user.avatar(), '<html/>')
	def should_get_user_group_plans(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('get', ['group-plans'], [MockData.GROUPS['illuminati']]),
			))

		user = habitica.user()
		groups = user.group_plans()
		self.assertEqual(groups[0].id, 'illuminati')
	def should_get_user_quest_daily_progress(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))

		user = habitica.user()
		progress = user.quest
		self.assertEqual(progress.key, 'laguardia1')
		self.assertEqual(progress.up, 'not-explained')
		self.assertEqual(progress.down, 'not-explained')
		self.assertEqual(progress.collected, 'not-explained')
		self.assertEqual(progress.collectedItems, 'not-explained')
		self.assertEqual(progress.completed, 'not-explained')
		self.assertFalse(progress.RSVPNeeded)
		self.assertTrue(progress.active)
	def should_get_member_achievements(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('get', ['members', 'jcdenton'], MockData.USER),
			MockDataRequest('get', ['members', 'jcdenton', 'achievements'], MockData.ACHIEVEMENTS),
			))

		member = habitica.member('pauldenton')
		achievements = member.achievements().basic
		self.assertEqual(achievements.label, 'Basic')
		self.assertEqual(len(achievements), 1)
		achievements = list(achievements)
		achievement = achievements[0]
		self.assertEqual(achievement.label, 'Basic')
		self.assertEqual(achievement.title, 'Sign Up')
		self.assertEqual(achievement.text, 'Sign Up with Habitica')
		self.assertEqual(achievement.icon, 'achievement-login')
		self.assertTrue(achievement.earned)
		self.assertEqual(achievement.value, 0)
		self.assertEqual(achievement.index, 60)
		self.assertEqual(achievement.optionalCount, 0)

		member = habitica.member('jcdenton')
		achievements = member.achievements().basic
		self.assertEqual(achievements.label, 'Basic')
		self.assertEqual(len(achievements), 1)
	def should_get_user_notifications(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['notifications', 'helios1', 'see'], {}),
			MockDataRequest('post', ['notifications', 'helios1', 'read'], {}),
			MockDataRequest('post', ['notifications', 'see'], {}),
			MockDataRequest('post', ['notifications', 'read'], {}),
			))

		user = habitica.user()
		notifications = user.notifications()
		first = next(iter(notifications))
		self.assertEqual(first.id, 'helios1')
		self.assertFalse(first.seen)
		first.mark_as_seen()
		self.assertTrue(first.seen)
		first.mark_as_read()
		notifications.mark_as_seen()
		notifications.mark_as_read()
	def should_create_task_for_user(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['tasks', 'user'], MockData.REWARDS['augments']),
			MockDataRequest('post', ['tasks', 'user'], MockData.HABITS['stealth']),
			))
		user = habitica.user()

		task = core.tasks.Reward(
				text='Use augmentation canister',
				value=100,
				)
		task = user.create_task(task)
		self.assertEqual(task.id, 'augments')

		task = core.tasks.Habit(
				text='Be quiet as possible',
				up=True,
				down=True,
				)
		task = user.create_task(task)
		self.assertEqual(task.id, 'stealth')
	def should_clear_completed_todos(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['tasks', 'clearCompletedTodos'], {}),
			))
		habitica.user.clearCompletedTodos()
	def should_allocate_stat_points(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'allocate'], MockData.USER['stats']),
			MockDataRequest('post', ['user', 'allocate-bulk'], MockData.USER['stats']),
			MockDataRequest('post', ['user', 'allocate-now'], MockData.USER['stats']),
			))
		user = habitica.user()
		user.stats.allocate(strength=1)
		user.stats.allocate(strength=2, perception=3, constitution=1, intelligence=5)
		user.stats.autoallocate_all()
	def should_change_class(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'change-class'], MockData.USER),
			))
		user = habitica.user()
		user.change_class('rogue')
	def should_disable_classes(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'disable-classes'], MockData.USER),
			))
		user = habitica.user()
		user.disable_classes()
	def should_equip_gear(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'equip', 'equipped', 'ninja_katana'], MockData.USER),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.equip_gear(habitica.content.armoire)
		user.equip_gear(habitica.content.gear('ninja_katana'))
	def should_wear_costume(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'equip', 'costume', 'ninja_katana'], MockData.USER),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.wear_costume(habitica.content.armoire)
		user.wear_costume(habitica.content.gear('ninja_katana'))
	def should_select_pet(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'equip', 'pet', 'fox'], MockData.USER),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.select_pet(habitica.content.armoire)
		user.select_pet(habitica.content.petInfo('fox'))
	def should_ride_mount(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'equip', 'mount', 'wolf'], MockData.USER),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.ride_mount(habitica.content.armoire)
		user.ride_mount(habitica.content.mountInfo('wolf'))
	def should_feed_pet(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'feed', 'fox', 'Meat'], 10),
			MockDataRequest('post', ['user', 'feed', 'fox', 'Meat'], 50),
			))
		user = habitica.user()
		user.inventory.pet.feed(habitica.content.food('Meat'))
		user.inventory.pet.feed(habitica.content.food('Meat'), 5)
	def should_hatch_pet(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'hatch', 'fox', 'base'], MockData.USER),
			))
		user = habitica.user()
		user.hatch_pet(habitica.content.dropEggs('fox'), habitica.content.hatchingPotions('base'))
	def should_rest_in_inn(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'sleep'], True),
			MockDataRequest('post', ['user', 'sleep'], False),
			))
		user = habitica.user()
		self.assertFalse(user.preferences.sleep)
		user.sleep()
		self.assertTrue(user.preferences.sleep)
		user.sleep()
		self.assertTrue(user.preferences.sleep)
		user.wake_up()
		self.assertFalse(user.preferences.sleep)
		user.wake_up()
		self.assertFalse(user.preferences.sleep)
	def should_read_special_card(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'read-card', 'congrats'], MockData.USER),
			))
		user = habitica.user()
		user.read_card(habitica.content.special_items('congrats'))
	def should_release_all_pets_and_mounts(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'release-mounts'], MockData.USER),
			MockDataRequest('post', ['user', 'release-both'], MockData.USER),
			))
		user = habitica.user()
		key = habitica.market().key_to_the_kennels
		user.buy(key)
		key = habitica.market().master_key_to_the_kennels
		user.buy(key)
	def should_reroll_tasks_using_fortify_potion(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'reroll'], MockData.USER),
			))
		user = habitica.user()
		potion = habitica.market().fortify_potion
		user.buy(potion)
	def should_revive_user_after_death(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'revive'], MockData.USER),
			))
		user = habitica.user()
		user.revive()
	def should_sell_items(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'hatchingPotions', 'base'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'hatchingPotions', 'base'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'eggs', 'wolf'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'eggs', 'wolf'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'food', 'Meat'], MockData.USER),
			MockDataRequest('post', ['user', 'sell', 'food', 'Meat'], MockData.USER),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.sell(habitica.content.petInfo('fox'))
		user.sell(habitica.content.hatchingPotions('base'))
		user.sell(habitica.content.hatchingPotions('base'), amount=5)
		user.sell(habitica.content.eggs('wolf'))
		user.sell(habitica.content.eggs('wolf'), amount=5)
		user.sell(habitica.content.food('Meat'))
		user.sell(habitica.content.food('Meat'), amount=5)
	def should_buy_orb_of_rebirth(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'rebirth'], MockData.USER),
			))
		user = habitica.user()
		orb = habitica.market().orb_of_rebirth
		user.buy(orb)
	def should_buy_background(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'unlock'], MockData.USER),
			MockDataRequest('post', ['user', 'unlock'], MockData.USER),
			))
		user = habitica.user()
		user.buy(habitica.content.get_background('blizzard'))
		self.assertEqual(habitica.api.responses[-1].params, {
			'path' : 'backgrounds.blizzard',
			})
		user.buy(habitica.content.get_background_set(2020, 8))
		self.assertEqual(habitica.api.responses[-1].params, {
			'path' : 'backgrounds.backgrounds082020',
			})

class TestNews(unittest.TestCase):
	def should_get_latest_news(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['news'], MockData.LATEST_NEWS),
			))
		news = habitica.news()
		self.assertEqual(news.html_text, '<h1>Latest news</h1>\n<p>Grey Death strikes again!</p>\n')
	def should_specific_news_post(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['news', 'greydeath'], MockData.NEWS),
			MockDataRequest('get', ['members', 'joegreen'], MockData.MEMBERS['joegreen']),
			))
		news = habitica.news('greydeath')
		self.assertEqual(news.title, 'Latest news')
		self.assertEqual(news.text, 'Grey Death strikes again!')
		self.assertEqual(news.credits, 'Joe Green')
		self.assertEqual(news.author.id, 'joegreen')
		self.assertEqual(news.publishDate, '2016-06-20T21:00:00.000Z')
		self.assertFalse(news.published)
	def should_postpone_news(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['news'], MockData.LATEST_NEWS),
			MockDataRequest('post', ['news', 'tell-me-later'], {}),
			))
		news = habitica.news()
		news.tell_me_later()
	def should_mark_news_as_read(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['news'], MockData.LATEST_NEWS),
			MockDataRequest('post', ['news', 'read'], {}),
			))
		news = habitica.news()
		news.mark_as_read()
		self.assertTrue(habitica.api.responses[-1].v4)

class TestQuest(unittest.TestCase):
	def should_show_progress_of_collection_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			))
		party = habitica.user().party()
		quest = party.quest
		self.assertTrue(quest.active)
		self.assertEqual(quest.key, 'laguardia1')
		self.assertEqual(quest.title, 'Find 3 more barrels of Ambrosia')
		self.assertEqual(quest.collect.current, 6)
		self.assertEqual(quest.collect.total, 8)
	def should_detect_if_quest_is_not_active(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['unatco']),
			))
		party = habitica.user().party()
		quest = party.quest
		self.assertIsNone(quest)
	def should_show_progress_of_boss_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['nsf']),
			MockDataRequest('get', ['members', 'jcdenton'], MockData.USER),
			))
		myguild = habitica.user.party()
		quest = myguild.quest
		self.assertTrue(quest.active)
		self.assertEqual(quest.key, '747')
		self.assertEqual(quest.title, 'Kill Anna Navarre')
		self.assertEqual(quest.leader().id, 'jcdenton')
		self.assertEqual(quest.boss.hp, 20)
		self.assertEqual(quest.boss.hp.max_value, 500)
	def should_show_progress_of_boss_rage(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['illuminati']),
			))
		myguild = habitica.user.party()
		quest = myguild.quest
		self.assertTrue(quest.active)
		self.assertEqual(quest.key, 'area51')
		self.assertAlmostEqual(quest.boss.rage.value, 1.05)
		self.assertAlmostEqual(quest.boss.rage.value.max_value, 500)
	def should_abort_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'abort'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.abort()
		party = habitica.user().party()
		quest = party.quest
		quest.abort()
	def should_accept_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'accept'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.accept()
		party = habitica.user().party()
		quest = party.quest
		quest.accept()
	def should_cancel_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'cancel'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.cancel()
		party = habitica.user().party()
		quest = party.quest
		quest.cancel()
	def should_force_start_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'force-start'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.force_start()
		party = habitica.user().party()
		quest = party.quest
		quest.force_start()
	def should_invite_group_members_to_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'invite', '747'], MockData.GROUPS['party']),
			))
		party = habitica.user().party()
		party.invite_to_quest(habitica.content.get_quest('747'))
	def should_leave_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'leave'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.leave()
		party = habitica.user().party()
		quest = party.quest
		quest.leave()
	def should_reject_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.GROUPS['party']),
			MockDataRequest('post', ['groups', 'party', 'quests', 'reject'], MockData.GROUPS['party']),
			))
		quest = habitica.content.get_quest('747')
		with self.assertRaises(RuntimeError):
			quest.reject()
		party = habitica.user().party()
		quest = party.quest
		quest.reject()

class TestTasks(unittest.TestCase):
	def should_operate_on_tags_in_task(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('get', ['tags'], MockData.ORDERED.TAGS),
			MockDataRequest('post', ['tasks', 'armory', 'tags', 'unatco'], dict(MockData.DAILIES['armory'], tags=[MockData.TAGS['unatco']])),
			MockDataRequest('get', ['tags'], MockData.ORDERED.TAGS),
			MockDataRequest('delete', ['tasks', 'armory', 'tags', 'unatco'], MockData.DAILIES['armory']),
			))
		user = habitica.user()
		tasks = user.dailies()
		task = tasks[0]
		tags = user.tags()
		tag = tags[2]
		task.add_tag(tag)
		self.assertEqual(task.tags[0].id, 'unatco')
		task.delete_tag(tag)
		self.assertEqual(len(user.tags()), 3)
	def should_approve_task_for_user(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('post', ['tasks', 'armory', 'approve', 'pauldenton'], MockData.DAILIES['armory']),
			))
		user = habitica.user()
		tasks = user.dailies()
		task = tasks[0]
		task.approve_for(habitica.member('pauldenton'))
	def should_assign_task_to_user(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('get', ['members', 'pauldenton'], MockData.MEMBERS['pauldenton']),
			MockDataRequest('post', ['tasks', 'armory', 'assign', 'pauldenton'], MockData.DAILIES['armory']),
			MockDataRequest('post', ['tasks', 'armory', 'unassign', 'pauldenton'], MockData.DAILIES['armory']),
			))
		user = habitica.user()
		tasks = user.dailies()
		task = tasks[0]
		paul = habitica.member('pauldenton')
		task.assign_to(paul)
		task.unassign_from(paul)
	def should_delete_task(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('delete', ['tasks', 'armory'], {}),
			))
		user = habitica.user()
		tasks = user.dailies()
		task = tasks[0]
		task.delete_task()
		self.assertIsNone(task.id)
	def should_rearrange_tasks(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'armory', 'move', 'to', '-1'], MockData.ORDERED.DAILIES),
			))
		user = habitica.user()
		tasks = user.dailies()
		tasks[0].move_to(-1)
	def should_require_more_work_for_group_tasks(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'armory', 'needs-work', 'jcdenton'], MockData.DAILIES['armory']),
			))
		user = habitica.user()
		tasks = user.dailies()
		tasks[0].needs_work(user)
	def should_unlink_from_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'unlink-one', 'armory'], {}),
			))
		user = habitica.user()
		tasks = user.dailies()
		tasks[0].unlink_from_challenge()

class TestRewards(unittest.TestCase):
	def should_get_user_rewards(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.REWARDS),
			))
		user = habitica.user()
		rewards = user.rewards()
		self.assertEqual(rewards[0].id, 'augments')
		self.assertEqual(rewards[0].text, 'Use augmentation canister')
		self.assertEqual(rewards[0].value, Price(100, 'gold'))
		self.assertEqual(rewards[1].id, 'read')
		self.assertEqual(rewards[1].text, 'Read "The man who was Thursday"')
	def should_buy_reward(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.REWARDS),
			MockDataRequest('post', ['tasks', 'augments', 'score', 'up'], {}),
			))
		user = habitica.user()
		rewards = user.rewards()
		user.buy(rewards[0])
	def should_update_reward(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.REWARDS),
			MockDataRequest('put', ['tasks', 'augments'], MockData.REWARDS['augments']),
			))
		user = habitica.user()
		rewards = user.rewards()
		rewards[0].update(
				text='Use augmentation canisters and upgrades',
				notes='Create a strong build.',
				tags=[],
				value=400,
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'notes': 'Create a strong build.',
			'tags': [],
			'text': 'Use augmentation canisters and upgrades',
			'value': 400,
			})

class TestEvents(unittest.TestCase):
	def should_handle_events_from_scoring_task(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			MockDataRequest('post', ['tasks', 'stealth', 'score', 'up'], {
				"_tmp": {
					"drop": {
						"dialog": "You've found a Cotton Candy Blue Hatching Potion!",
						},
					"quest": {
						"progressDelta": 0.6949999999999932
						}
					},
				"class": "warrior",
				"con": 0,
				"delta": 1,
				"exp": 189,
				"gp": 820.2457348942492,
				"hp": 50,
				"int": 28,
				"lvl": 36,
				"mp": 13.139782544906312,
				"per": 8,
				"points": 0,
				"str": 0,
				}),
			))
		user = habitica.user()
		habits = user.habits()
		habits[5].up()
		self.assertEqual(list(map(str, habitica.events.dump())), [
			"You've found a Cotton Candy Blue Hatching Potion!",
			"Quest progress: +0.695",
			"Class changed from 'rogue' to 'warrior'",
			"Gp: +805.246",
			])

class TestHabits(unittest.TestCase):
	def should_get_list_of_user_habits(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			))
		user = habitica.user()
		habits = user.habits()
		self.assertEqual(habits[0].id, 'bobpage')
		self.assertEqual(habits[0].text, 'Join Bob Page')
		self.assertEqual(habits[0].notes, '')
		self.assertEqual(habits[0].value, -50.1)
		self.assertEqual(habits[0].color, core.Task.DARK_RED)
		self.assertTrue(habits[0].can_score_up)
		self.assertFalse(habits[0].can_score_down)

		self.assertEqual(habits[5].counterUp, 3)
		self.assertEqual(habits[5].counterDown, 1)
		self.assertEqual(habits[5].frequency, 'daily')
	def should_separate_habits_by_color(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			))
		user = habitica.user()
		habits = sorted(user.habits(), key=lambda _:_.value)
		self.assertEqual(habits[0].color, core.Task.DARK_RED)
		self.assertEqual(habits[1].color, core.Task.RED)
		self.assertEqual(habits[2].color, core.Task.ORANGE)
		self.assertEqual(habits[3].color, core.Task.YELLOW)
		self.assertEqual(habits[4].color, core.Task.GREEN)
		self.assertEqual(habits[5].color, core.Task.LIGHT_BLUE)
		self.assertEqual(habits[6].color, core.Task.BRIGHT_BLUE)
	def should_score_habits_up(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			MockDataRequest('post', ['tasks', 'stealth', 'score', 'up'], {
				'delta' : 1.1,
				}),
			))
		user = habitica.user()
		habits = user.habits()
		habits[5].up()
		self.assertAlmostEqual(habits[5].value, 6.2)
		with self.assertRaises(core.CannotScoreUp) as e:
			habits[1].up()
		self.assertEqual(str(e.exception), "Habit 'Carry on, agent' cannot be incremented")
	def should_score_habits_down(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			MockDataRequest('post', ['tasks', 'stealth', 'score', 'down'], {
				'delta' : -1.1,
				}),
			))
		user = habitica.user()
		habits = user.habits()
		habits[5].down()
		self.assertAlmostEqual(habits[5].value, 4.0)
		with self.assertRaises(core.CannotScoreDown) as e:
			habits[1].down()
		self.assertEqual(str(e.exception), "Habit 'Carry on, agent' cannot be decremented")
	def should_update_habit(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.HABITS),
			MockDataRequest('put', ['tasks', 'stealth'], {}),
			))
		user = habitica.user()
		habits = user.habits()
		habit = habits[5]
		habit.update(
				text='Use Stealth ability',
				notes='Upgrade as much as possible',
				attribute="dex",
				collapseChecklist=True,
				priority=core.tasks.Task.Priority.MEDIUM,
				reminders=['not-explained'],
				tags=[],
				up=False,
				down=True,
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'text' : 'Use Stealth ability',
			'notes' : 'Upgrade as much as possible',
			'attribute' : "dex",
			'collapseChecklist' : True,
			'priority' : core.tasks.Task.Priority.MEDIUM,
			'reminders' : ['not-explained'],
			'tags' : [],
			'up' : False,
			'down' : True,
			})

class TestDailies(unittest.TestCase):
	def should_get_list_of_user_dailies(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			))
		user = habitica.user()
		dailies = user.dailies()
		self.assertEqual(dailies[0].id, 'armory')
		self.assertEqual(dailies[0].text, 'Restock at armory')
		self.assertEqual(dailies[0].notes, 'See Sam Carter for equipment')
		self.assertFalse(dailies[0].is_completed)
		self.assertEqual(dailies[0].streak, 3)
		self.assertFalse(dailies[0].yesterDaily)
		self.assertTrue(dailies[0].isDue)
		self.assertFalse(dailies[0].collapseChecklist)
		self.assertEqual(dailies[0].nextDue, '2016-06-20T21:00:00.000Z')

		checklist = dailies[0].checklist
		self.assertEqual(checklist[0].id, 'stealthpistol')
		self.assertEqual(checklist[0].text, 'Ask for stealth pistol')
		self.assertTrue(checklist[0].is_completed)
		self.assertEqual(checklist[0].parent.id, 'armory')

		self.assertEqual(dailies[0][1].id, 'lockpick')
		self.assertEqual(dailies[0][1].text, 'Choose lockpick')
		self.assertFalse(dailies[0][1].is_completed)
	def should_detect_due_dailies(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			))
		user = habitica.user()
		dailies = user.dailies()

		daily = dailies[1]
		trigger = daily.trigger
		self.assertEqual(timeutils.parse_isodate(trigger.startDate.replace('T', ' ').replace('Z', '')).date(), datetime.date(2016, 6, 20))
		self.assertEqual(trigger.everyX, 12)
		self.assertEqual(trigger.daysOfMonth, 1)
		self.assertEqual(trigger.weeksOfMonth, 1)

		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-09 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-10 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(daily.is_due(today=timeutils.parse_isodate('2016-11-11 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-12 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(daily.is_due(today=timeutils.parse_isodate('2016-11-23 16:51:15.930842'), timezoneOffset=-120))

		daily = dailies[2]
		trigger = daily.trigger
		self.assertEqual(trigger.weekdays, [0])
		self.assertTrue(trigger.monday)
		self.assertFalse(trigger.tuesday)
		self.assertFalse(trigger.wednesday)
		self.assertFalse(trigger.thursday)
		self.assertFalse(trigger.friday)
		self.assertFalse(trigger.saturday)
		self.assertFalse(trigger.sunday)

		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-09 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-10 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-11 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-12 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-13 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(daily.is_due(today=timeutils.parse_isodate('2016-11-14 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-15 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(daily.is_due(today=timeutils.parse_isodate('2016-11-16 16:51:15.930842'), timezoneOffset=-120))
	def should_complete_daily(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'armory', 'score', 'up'], {'delta':1}),
			MockDataRequest('post', ['tasks', 'armory', 'score', 'down'], {'delta':-1}),
			))
		user = habitica.user()
		dailies = user.dailies()
		self.assertFalse(dailies[0].is_completed)

		dailies[0].complete()
		self.assertTrue(dailies[0].is_completed)

		dailies[0].undo()
		self.assertFalse(dailies[0].is_completed)
	def should_complete_check_items(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'armory', 'checklist', 'stealthpistol', 'score'], {}),
			MockDataRequest('post', ['tasks', 'armory', 'checklist', 'lockpick', 'score'], {}),
			))
		user = habitica.user()
		dailies = user.dailies()
		daily = dailies[0]

		self.assertFalse(daily.is_completed)

		daily[0].complete()
		self.assertTrue(daily[0].is_completed)
		daily[0].undo()
		self.assertFalse(daily[0].is_completed)

		daily[1].undo()
		self.assertFalse(daily[1].is_completed)
		daily[1].complete()
		self.assertTrue(daily[1].is_completed)
	def should_operate_on_items_in_checklist(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('post', ['tasks', 'armory', 'checklist'], MockData.DAILIES['armory']),
			MockDataRequest('put', ['tasks', 'armory', 'checklist', 'lockpick'], MockData.DAILIES['armory']),
			MockDataRequest('delete', ['tasks', 'armory', 'checklist', 'lockpick'], MockData.DAILIES['armory']),
			))
		user = habitica.user()
		tasks = user.dailies()
		task = tasks[0]
		task.append('Get medkits')
		task[1].update('Get medkits from medbay')
		task.delete(task[1])
	def should_update_daily(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.DAILIES),
			MockDataRequest('put', ['tasks', 'armory'], MockData.DAILIES['armory']),
			MockDataRequest('put', ['tasks', 'manderley'], MockData.DAILIES['manderley']),
			MockDataRequest('put', ['tasks', 'manderley'], MockData.DAILIES['manderley']),
			MockDataRequest('put', ['tasks', 'medbay'], MockData.DAILIES['medbay']),
			))
		user = habitica.user()
		tasks = user.dailies()

		task = tasks[0]
		task.update(
				streak=12,
				frequency=core.tasks.WeeklyFrequency(
					monday=True,
					tuesday=False,
					wednesday=False,
					thursday=False,
					friday=False,
					saturday=False,
					sunday=False,
					),
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'streak' : 12,
			'frequency' : 'weekly',
			'repeat':{
				"m":True,
				"t":False,
				"w":False,
				"th":False,
				"f":False,
				"s":False,
				"su":False,
				},
			})

		task = tasks[1]
		task.update(
				frequency=core.tasks.DailyFrequency(
					startDate='today',
					),
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'startDate' : 'today',
			})

		task = tasks[1]
		task.update(
				frequency=core.tasks.DailyFrequency(
					everyX=7,
					),
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'everyX' : 7,
			})

		task = tasks[2]
		task.update(
				frequency=core.tasks.DailyFrequency(
					startDate='today',
					everyX=7,
					),
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'frequency' : 'daily',
			'startDate' : 'today',
			'everyX' : 7,
			})

class TestTodos(unittest.TestCase):
	def should_get_list_of_user_todos(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.TODOS),
			MockDataRequest('get', ['groups', 'unatco'], MockData.GROUPS['unatco']),
			MockDataRequest('get', ['challenges', 'unatco'], MockData.CHALLENGES['unatco']),
			))
		user = habitica.user()
		todos = user.todos()
		todo = todos[1]

		self.assertEqual(todo.id, 'majestic12')
		self.assertEqual(todo.type, 'todo')
		self.assertEqual(todo.text, 'Escape Majestic 12 facilities')
		self.assertEqual(todo.notes, 'Be stealth as possible')
		self.assertFalse(todo.is_completed)
		self.assertEqual(todo.createdAt, 1600000000)
		self.assertEqual(todo.updatedAt, 1600000000)
		self.assertFalse(todo.byHabitica)
		self.assertEqual(todo.alias, 'escape')
		self.assertEqual(todo.priority, 'not-explained')
		self.assertEqual(todo.attribute, 'dex')
		self.assertEqual(todo.userId, 'jcdenton')
		self.assertEqual(todo.reminders[0], 'not-explained')

		checklist = todo.checklist
		self.assertEqual(checklist[0].id, 'armory')
		self.assertEqual(checklist[0].text, 'Get back all equipment')
		self.assertTrue(checklist[0].is_completed)
		self.assertEqual(checklist[0].parent.id, 'majestic12')

		self.assertEqual(todo[1].id, 'killswitch')
		self.assertEqual(todo[1].text, 'Get killswitch schematics from medlab')
		self.assertFalse(todo[1].is_completed)

		todo = todos[0]
		self.assertEqual(todo.date, datetime.date(2016, 6, 20))
		self.assertEqual(todo.dateCompleted, datetime.date(3000, 1, 1))

		group = todo.group
		self.assertFalse(group.broken)
		self.assertEqual(group.assignedUsers, ['jcdenton'])
		self.assertEqual(group.assignedDate, 'DATE')
		self.assertEqual(group.assignedUsername, 'pauldenton')
		self.assertEqual(group.taskId, todo.id)
		self.assertFalse(group.sharedCompletion)
		self.assertEqual(group.managerNotes, 'Track progress of agent.')
		self.assertEqual(group().id, 'unatco')
		approval = group.approval
		self.assertTrue(approval.required)
		self.assertTrue(approval.requested)
		self.assertEqual(approval.requestedDate, 'DATE')
		self.assertEqual(approval.dateApproved, 'DATE')
		self.assertEqual(approval.approvingUser, 'manderley')

		challenge = todo.challenge
		self.assertEqual(challenge.shortName, 'UNATCO')
		self.assertEqual(challenge.taskId, todo.id)
		self.assertTrue(challenge.broken)
		self.assertEqual(challenge.winner, 'jcdenton')
		self.assertEqual(challenge().id, 'unatco')
	def should_complete_todo(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.TODOS),
			MockDataRequest('post', ['tasks', 'majestic12', 'score', 'up'], {'delta':1}),
			MockDataRequest('post', ['tasks', 'majestic12', 'score', 'down'], {'delta':-1}),
			))
		user = habitica.user()
		todos = user.todos()
		todo = todos[1]

		self.assertFalse(todo.is_completed)

		todo.complete()
		self.assertTrue(todo.is_completed)

		todo.undo()
		self.assertFalse(todo.is_completed)
	def should_complete_check_items(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.TODOS),
			MockDataRequest('post', ['tasks', 'majestic12', 'checklist', 'armory', 'score'], {}),
			MockDataRequest('post', ['tasks', 'majestic12', 'checklist', 'killswitch', 'score'], {}),
			))
		user = habitica.user()
		todos = user.todos()

		todo = todos[1]
		self.assertFalse(todo.is_completed)

		todo[0].complete()
		self.assertTrue(todo[0].is_completed)
		todo[0].undo()
		self.assertFalse(todo[0].is_completed)

		todo[1].undo()
		self.assertFalse(todo[1].is_completed)
		todo[1].complete()
		self.assertTrue(todo[1].is_completed)
	def should_update_todo(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.TODOS),
			MockDataRequest('put', ['tasks', 'liberty'], {}),
			))
		user = habitica.user()
		todos = user.todos()
		todo = todos[0]
		todo.update(
				text='Liberate Liberty statue',
				notes='and resque agents',
				collapseChecklist=False,
				priority=core.tasks.Task.Priority.HARD,
				date=datetime.date.today(),
				)
		self.assertEqual(habitica.api.responses[-1].body, {
			'text' : 'Liberate Liberty statue',
			'notes' : 'and resque agents',
			'collapseChecklist' : False,
			'priority' : core.tasks.Task.Priority.HARD,
			'date' : str(datetime.date.today()),
			})

class TestSpells(unittest.TestCase):
	def should_get_full_list_of_spells_for_user(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			))
		user = habitica.user()
		spells = sorted(user.spells(), key=lambda s:s.key)
		self.assertEqual(spells[0].key, 'backStab')
		self.assertEqual(spells[1].key, 'stealth')
	def should_get_specific_spell(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			))
		user = habitica.user()
		spell = user.get_spell('stealth')
		self.assertEqual(spell.key, 'stealth')
		self.assertEqual(spell.text, "Stealth")
	def should_cast_spell(self):
		updated_stats = copy.deepcopy(MockData.USER['stats'])
		updated_stats['buffs']['per'] = 100

		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'class', 'cast', 'stealth'], {'user':{'stats':updated_stats}}),
			MockDataRequest('get', ['tasks', 'user'], MockData.ORDERED.TODOS),
			MockDataRequest('post', ['user', 'class', 'cast', 'backStab'], {'task':{
				'value' : -1.2,
				}}),
			))
		user = habitica.user()
		with self.assertRaises(RuntimeError):
			user.cast(user.inventory.pet)
		spell = user.get_spell('stealth')
		user.cast(spell)
		self.assertEqual(user.stats.buffs.perception, 100)
		target = user.todos()[0]
		spell = user.get_spell('backStab')
		user.cast(spell, target)
		self.assertEqual(target.value, -1.2)

class TestTags(unittest.TestCase):
	def should_create_new_tag(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['tags'], MockData.ORDERED.TAGS[1]),
			))
		tag = habitica.create_tag('Side Quest')
		self.assertEqual(tag.id, 'side')
		self.assertEqual(tag.name, 'Side Quest')
		self.assertIsNone(tag.group())
		self.assertFalse(tag.is_challenge)
	def should_get_tag(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['tags', 'nsf'], MockData.ORDERED.TAGS[0]),
			MockDataRequest('get', ['groups', 'nsf'], MockData.GROUPS['nsf']),
			))
		tag = habitica._get_tag('nsf')
		self.assertEqual(tag.id, 'nsf')
		self.assertEqual(tag.name, 'NSF')
		self.assertEqual(tag.group().id, 'nsf')
		self.assertFalse(tag.is_challenge)
	def should_get_tags(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['tags'], MockData.ORDERED.TAGS),
			))
		tags = habitica.user.tags()
		self.assertEqual(tags[0].id, 'nsf')
		self.assertEqual(tags[2].id, 'unatco')
	def should_delete_tag(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['tags', 'unatco'], MockData.ORDERED.TAGS[2]),
			MockDataRequest('delete', ['tags', 'unatco'], {}),
			))
		tag = habitica._get_tag('unatco')
		tag.delete()
	def should_reorder_tags(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['tags', 'unatco'], MockData.ORDERED.TAGS[2]),
			MockDataRequest('post', ['reorder-tags'], {}),
			))
		tag = habitica._get_tag('unatco')
		tag.move_to(0)
	def should_rename_tag(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['tags', 'unatco'], MockData.ORDERED.TAGS[2]),
			MockDataRequest('put', ['tags', 'unatco'], dict(MockData.ORDERED.TAGS[2], name='Ex-UNATCO')),
			))
		tag = habitica._get_tag('unatco')
		tag.rename('Ex-UNATCO')
		self.assertEqual(tag.name, 'Ex-UNATCO')

class TestContent(unittest.TestCase):
	def should_retrieve_health_potion(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		potion = content.potion
		self.assertEqual(potion.text, 'Health Potion')
		self.assertEqual(potion.key, 'HealthPotion')
		self.assertEqual(potion.notes, 'Heals 15 hp')
		self.assertEqual(potion.type, 'potion')
		self.assertEqual(potion.cost, Price(25, 'gold'))
	def should_retrieve_armoire(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		armoire = content.armoire
		self.assertEqual(armoire.text, 'Enchanted Armoire')
		self.assertEqual(armoire.key, 'Armoire')
		self.assertEqual(armoire.type, 'armoire')
		self.assertEqual(armoire.cost, Price(100, 'gold'))
	def should_list_available_classes(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		self.assertEqual(sorted(content.classes), [
			'healer',
			'rogue',
			'warrior',
			'wizard',
			])
	def should_list_gear_types(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		self.assertEqual(sorted(content.gearTypes), [
			"armor",
			"head",
			"headAccessory",
			])
	def should_retrieve_food(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		food = sorted(content.food(), key=lambda _:_.key)[1]
		self.assertEqual(food.key, 'Meat')
		self.assertEqual(food.text, 'Meat')
		self.assertEqual(food.notes, 'A piece of meat.')
		self.assertEqual(food.textA, 'A meat')
		self.assertEqual(food.textThe, 'The Meat')
		self.assertEqual(food.target, 'Base')
		self.assertTrue(food.canDrop)
	def should_retrieve_various_eggs(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		egg = content.questEggs()[0]
		self.assertEqual(egg.key, 'badger')
		self.assertEqual(egg.text, 'Badger')
		self.assertEqual(egg.mountText, 'Badger')
		self.assertEqual(egg.notes, 'This is a Badger egg.')
		self.assertEqual(egg.adjective, 'serious')
		self.assertEqual(egg.price, Price(4, 'gems'))

		egg = content.eggs()[0]
		self.assertEqual(egg.key, 'wolf')
		self.assertEqual(egg.text, 'Wolf')
		self.assertEqual(egg.mountText, 'Wolf')
		self.assertEqual(egg.notes, 'This is a Wolf egg.')
		self.assertEqual(egg.adjective, 'fierce')
		self.assertEqual(egg.price, Price(3, 'gems'))

		egg = content.dropEggs()[0]
		self.assertEqual(egg.key, 'fox')
		self.assertEqual(egg.text, 'Fox')
		self.assertEqual(egg.mountText, 'Fox')
		self.assertEqual(egg.notes, 'This is a Fox egg.')
		self.assertEqual(egg.adjective, 'sly')
		self.assertEqual(egg.price, Price(2, 'gems'))
	def should_retrieve_various_hatching_potions(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		potion = content.hatchingPotions()[0]
		self.assertEqual(potion.key, 'base')
		self.assertEqual(potion.text, 'Base')
		self.assertEqual(potion.notes, 'Makes Base pet.')
		self.assertEqual(potion._addlNotes, '')
		self.assertEqual(potion.price, Price(2, 'gems'))
		self.assertFalse(potion.premium)
		self.assertFalse(potion.limited)
		self.assertFalse(potion.wacky)
		self.assertIsNone(potion.event)

		potion = content.wackyHatchingPotions()[0]
		self.assertEqual(potion.key, 'wacky')
		self.assertEqual(potion.text, 'Wacky')
		self.assertEqual(potion.notes, 'Makes Wacky pet.')
		self.assertEqual(potion._addlNotes, 'Wacky!')
		self.assertEqual(potion.price, Price(3, 'gems'))
		self.assertTrue(potion.premium)
		self.assertTrue(potion.limited)
		self.assertTrue(potion.wacky)
		self.assertEqual(potion.event.start, datetime.date(2020, 1, 1))
		self.assertEqual(potion.event.end, datetime.date(2020, 1, 31))

		potion = content.dropHatchingPotions()[0]
		self.assertEqual(potion.key, 'red')
		self.assertEqual(potion.text, 'Red')
		self.assertEqual(potion.notes, 'Makes Red pet.')
		self.assertEqual(potion._addlNotes, '')
		self.assertEqual(potion.price, Price(4, 'gems'))
		self.assertFalse(potion.premium)
		self.assertTrue(potion.limited)
		self.assertFalse(potion.wacky)
		self.assertIsNone(potion.event)

		potion = content.premiumHatchingPotions()[0]
		self.assertEqual(potion.key, 'shadow')
		self.assertEqual(potion.text, 'Shadow')
		self.assertEqual(potion.notes, 'Makes Shadow pet.')
		self.assertEqual(potion._addlNotes, 'Premium!')
		self.assertEqual(potion.price, Price(5, 'gems'))
		self.assertTrue(potion.premium)
		self.assertFalse(potion.limited)
		self.assertFalse(potion.wacky)
		self.assertIsNone(potion.event)
	def should_retrieve_various_pets(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		pet = content.petInfo('fox')
		self.assertEqual(pet.key, 'fox')
		self.assertEqual(pet.text, 'Fox')
		self.assertEqual(pet.type, 'Base')
		self.assertEqual(pet.egg, 'fox')
		self.assertEqual(pet.potion, 'base')
		self.assertTrue(pet.canFind)
		self.assertFalse(pet.special)

		pet_names = [pet.text for pet in content.petInfo()]
		self.assertEqual(sorted(pet_names), ['Badger', 'Fox'])

		pet = content.questPets()[0]
		self.assertEqual(pet.key, 'fox')
		self.assertEqual(str(pet), 'Fox')

		pet = content.premiumPets()[0]
		self.assertEqual(pet.key, 'fox')

		pet = content.specialPets()[0]
		self.assertEqual(pet.key, 'badger')
		self.assertEqual(pet.text, 'Badger')
		self.assertEqual(pet.type, 'Clockwork')
		self.assertEqual(pet.egg, 'badger')
		self.assertIsNone(pet.potion)
		self.assertIsNone(pet.canFind)
		self.assertTrue(pet.special)
	def should_retrieve_various_mounts(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		mount = content.mountInfo('fox')
		self.assertEqual(mount.key, 'fox')
		self.assertEqual(mount.text, 'Fox')
		self.assertEqual(mount.type, 'Base')
		self.assertEqual(mount.egg, 'fox')
		self.assertEqual(mount.potion, 'base')
		self.assertTrue(mount.canFind)
		self.assertFalse(mount.special)

		mount_names = [mount.text for mount in content.mountInfo()]
		self.assertEqual(sorted(mount_names), ['Fox', 'Wolf'])

		mount = content.mounts()[0]
		self.assertEqual(mount.key, 'fox')

		mount = content.questMounts()[0]
		self.assertEqual(mount.key, 'fox')
		self.assertEqual(str(mount), 'Fox')

		mount = content.premiumMounts()[0]
		self.assertEqual(mount.key, 'fox')

		self.assertIsNone(content.specialMounts('fox'))
		mount = content.specialMounts()[0]
		self.assertEqual(mount.key, 'wolf')
		self.assertEqual(mount.text, 'Wolf')
		self.assertEqual(mount.type, 'Clockwork')
		self.assertEqual(mount.egg, 'wolf')
		self.assertIsNone(mount.potion)
		self.assertIsNone(mount.canFind)
		self.assertTrue(mount.special)
	def should_get_single_backgroud(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		background = content.get_background('blizzard')
		self.assertEqual(background.key, 'blizzard')
		self.assertEqual(background.text, 'Blizzard')
		self.assertEqual(background.notes, 'Hurling Blizzard')
		self.assertEqual(background.price, Price(7, 'gems'))
		self.assertEqual(background.set_name, 'Winter')
	def should_get_backgroud_set(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		backgrounds = content.get_background_set(2020, 8)
		self.assertEqual(backgrounds.key, 'backgrounds082020')
		self.assertEqual(backgrounds[0].key, 'fall')
		self.assertEqual(backgrounds[0].text, 'Fall')
		self.assertEqual(backgrounds[0].notes, "Summer's End")
		self.assertEqual(backgrounds[0].price, Price(7, 'gems'))
		self.assertEqual(backgrounds[0].set_name, 'Fall')

		backgrounds = sorted(content.get_background_set(2020), key=lambda _:_.key)
		self.assertEqual(backgrounds[0].key, 'backgrounds082020')
		self.assertEqual(backgrounds[0][0].key, 'fall')
		self.assertEqual(backgrounds[1][0].key, 'blizzard')

		backgrounds = content.get_background_set(None)
		self.assertEqual(backgrounds[0].key, 'core')
		self.assertEqual(backgrounds[0].text, 'The Core')
		self.assertEqual(backgrounds[0].notes, "The Core")
		self.assertEqual(backgrounds[0].price, Price(1, 'hourglass'))
		self.assertEqual(backgrounds[0].set_name, 'timeTravel')
	def should_get_special_items(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		items = sorted(content.special_items(), key=lambda _:_.key)

		item = items[0]
		self.assertEqual(item.key, 'congrats')
		self.assertEqual(item.text, 'Congratulations Card')
		self.assertEqual(item.notes, 'Send a Congratulations card to a party member.')
		self.assertIsNone(item.purchaseType)
		self.assertEqual(item.mana, 0)
		self.assertEqual(item.target, 'user')
		self.assertEqual(item.price, Price(10, 'gold'))
		self.assertFalse(item.previousPurchase)
		self.assertTrue(item.silent)
		self.assertTrue(item.immediateUse)
		self.assertTrue(item.yearRound)
		self.assertEqual(item.messageOptions, 5)

		item = items[1]
		self.assertEqual(item.key, 'petalFreePotion')
		self.assertEqual(item.text, 'Petal-Free Potion')
		self.assertEqual(item.notes, 'Reverse the spell that made you a flower.')
		self.assertEqual(item.purchaseType, 'debuffPotion')
		self.assertEqual(item.mana, 0)
		self.assertEqual(item.target, 'self')
		self.assertEqual(item.price, Price(5, 'gold'))
		self.assertFalse(item.previousPurchase)
		self.assertFalse(item.silent)
		self.assertTrue(item.immediateUse)
		self.assertFalse(item.yearRound)
		self.assertIsNone(item.messageOptions)

		item = items[2]
		self.assertEqual(item.key, 'shinySeed')
		self.assertEqual(item.text, 'Shiny Seed')
		self.assertEqual(item.notes, 'Turn a friend into a joyous flower!')
		self.assertIsNone(item.purchaseType)
		self.assertEqual(item.mana, 0)
		self.assertEqual(item.target, 'user')
		self.assertEqual(item.price, Price(15, 'gold'))
		self.assertTrue(item.previousPurchase)
		self.assertFalse(item.silent)
		self.assertFalse(item.immediateUse)
		self.assertFalse(item.yearRound)
		self.assertIsNone(item.messageOptions)
	def should_get_cards(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		items = content.cards()
		self.assertEqual(len(items), 1)

		item = items[0]
		self.assertEqual(item.key, 'congrats')
	def should_get_spells_for_class(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		spells = sorted(content.spells('rogue'), key=lambda _:_.key)
		spell = spells[1]
		self.assertEqual(spell.key, 'stealth')
		self.assertEqual(spell.text, 'Stealth')
		self.assertEqual(spell.notes, 'Be a Ninja')
		self.assertEqual(spell.lvl, 14)
		self.assertEqual(spell.mana, 45)
		self.assertEqual(spell.target, 'self')

		spell = content.get_spell('rogue', 'stealth')
		self.assertEqual(spell.key, 'stealth')
	def should_have_quest_with_boss(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		quest = content.get_quest('747')

		self.assertEqual(quest.key, '747')
		self.assertEqual(quest.text, 'Kill Anna Navarre')
		self.assertEqual(quest.notes, 'Additional notes')
		self.assertTrue(quest.userCanOwn)
		self.assertEqual(quest.category, 'pet')
		self.assertIsNone(quest.unlockCondition)

		self.assertFalse(quest.active)
		self.assertIsNone(quest.leader())

		self.assertEqual(quest.level, 33)
		self.assertIsNone(quest.goldValue)
		self.assertEqual(quest.group, 'nsf')
		self.assertEqual(quest.previous.key, 'laguardia1')
		self.assertEqual(quest.completion, 'You killed Anna Navarre!')
		self.assertIsNone(quest.completionChat)
		self.assertEqual(quest.colors, {})
		self.assertIsNone(quest.event)

		drop = quest.drop
		self.assertEqual(drop.unlock, '')
		self.assertEqual(drop.experience, 200)
		self.assertEqual(drop.gold, 10)
		items = drop.items
		self.assertEqual(items[0].key, 'fox')
		self.assertEqual(items[0].text, 'Fox Egg')
		self.assertEqual(items[0].type, 'dropEggs')
		self.assertFalse(items[0].onlyOwner)
		self.assertEqual(items[0].get_content_entry().key, 'fox')

		self.assertIsNone(quest.collect)
		boss = quest.boss
		self.assertEqual(boss.name, 'Anna Navarre')
		self.assertEqual(boss.strength, 1)
		self.assertEqual(boss.defense, 0.5)
		self.assertEqual(boss.hp, 500)
		self.assertIsNone(boss.rage)
	def should_have_quest_with_collection(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		quest = content.get_quest('laguardia1')

		self.assertEqual(quest.key, 'laguardia1')
		self.assertEqual(quest.text, 'Find 3 more barrels of Ambrosia')
		self.assertEqual(quest.notes, 'Also deactivate 5 turret towers')
		self.assertTrue(quest.userCanOwn)
		self.assertEqual(quest.category, 'unlockable')
		self.assertEqual(quest.goldValue, Price(10, 'gold'))
		self.assertEqual(quest.group, 'unatco')
		self.assertIsNone(quest.previous)
		self.assertEqual(quest.completion, 'You have found all 4 Ambrosia containers!')
		self.assertIsNone(quest.completionChat)
		self.assertEqual(quest.colors, {})
		self.assertIsNone(quest.event)

		condition = quest.unlockCondition
		self.assertEqual(condition.text, 'Swipe to unlock')
		self.assertEqual(condition.condition, 'login')
		self.assertEqual(condition.incentiveThreshold, 3)

		drop = quest.drop
		self.assertEqual(drop.unlock, '')
		self.assertEqual(drop.experience, 500)
		self.assertEqual(drop.gold, 100)
		items = drop.items
		self.assertEqual(items[0].key, '747')
		self.assertEqual(items[0].text, 'Kill Anna Navarre')
		self.assertEqual(items[0].type, 'quests')
		self.assertTrue(items[0].onlyOwner)
		self.assertEqual(items[0].get_content_entry().key, '747')

		self.assertIsNone(quest.boss)
		collect = quest.collect
		self.assertEqual(set(collect.names), {'ambrosia', 'turret'})
		item = collect.get_item('ambrosia')
		self.assertEqual(item.key, 'ambrosia')
		self.assertEqual(item.text, 'Barrel of Ambrosia', 3)
		self.assertEqual(item.amount, 3)
		item = collect.get_item('turret')
		self.assertEqual(item.key, 'turret')
		self.assertEqual(item.text, 'Turret')
		self.assertEqual(item.amount, 5)
		collect_items = sorted(collect.items(), key=lambda _:_.key)
		item = collect_items[0]
		self.assertEqual(item.key, 'ambrosia')
		self.assertEqual(item.text, 'Barrel of Ambrosia', 3)
		self.assertEqual(item.amount, 3)
		item = collect_items[1]
		self.assertEqual(item.key, 'turret')
		self.assertEqual(item.text, 'Turret')
		self.assertEqual(item.amount, 5)
		self.assertEqual(collect.total, 8)
	def should_have_world_quest(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		quest = content.get_quest('area51')

		self.assertEqual(quest.key, 'area51')
		self.assertEqual(quest.text, 'Join Illuminati')
		self.assertEqual(quest.notes, 'Kill Bob Page')
		self.assertFalse(quest.userCanOwn)
		self.assertEqual(quest.category, 'world')
		self.assertIsNone(quest.goldValue)
		self.assertIsNone(quest.group)
		self.assertIsNone(quest.previous)
		self.assertEqual(quest.completion, 'You have joined Illuminati!')
		self.assertEqual(quest.completionChat, 'You have joined Illuminati!')
		self.assertEqual(quest.colors, {'main':'#ffffff'})
		self.assertEqual(quest.event.start, datetime.date(2020, 1, 1))
		self.assertEqual(quest.event.end, datetime.date(2020, 1, 31))

		drop = quest.drop
		self.assertFalse(drop.unlock)
		self.assertEqual(drop.experience, 0)
		self.assertEqual(drop.gold, 0)
		items = drop.items
		self.assertEqual(items[0].key, 'fox')
		self.assertEqual(items[0].text, 'Fox pet')
		self.assertEqual(items[0].type, 'questPets')
		self.assertFalse(items[0].onlyOwner)
		self.assertEqual(items[0].get_content_entry().key, 'fox')

		self.assertIsNone(quest.collect)
		boss = quest.boss
		self.assertEqual(boss.name, 'Bob Page')
		self.assertEqual(boss.strength, 5)
		self.assertEqual(boss.defense, 1.5)
		self.assertEqual(boss.hp, 50000)
		rage = boss.rage
		self.assertEqual(rage.value, 500)
		self.assertEqual(rage.title, 'Boss Rage')
		self.assertEqual(rage.healing, 100)
		self.assertIsNone(rage.mpDrain)
		self.assertEqual(rage.description, 'When rage is filled, boss rages!')
		self.assertEqual(rage.effect, 'Boss rages!')
		self.assertEqual(rage.stables, 'Boss rages!')
		self.assertEqual(rage.bailey, 'Boss rages!')
		self.assertEqual(rage.guide, 'Boss rages!')
		self.assertEqual(rage.tavern, 'Boss rages!')
		self.assertEqual(rage.quests, 'Boss rages!')
		self.assertIsNone(rage.seasonalShop)
		self.assertIsNone(rage.market)
	def should_get_gear_directly(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		gear = content.gear('ninja_katana')
		self.assertEqual(gear.key, 'ninja_katana')
		self.assertEqual(gear.text, 'Katana')
		self.assertEqual(gear.notes, 'Ninja Katana.')
		self.assertEqual(gear.klass, 'rogue')
		self.assertEqual(gear.class_name, 'rogue')
		self.assertIsNone(gear.specialClass)
		self.assertFalse(gear.is_special)
		self.assertIsNone(gear.event)
		self.assertEqual(gear.set_name, 'ninja-1')
		self.assertEqual(gear.index, '1')
		self.assertEqual(gear.type, 'weapon')
		self.assertEqual(gear.value, Price(100, 'gold'))
		self.assertEqual(gear.str, 5)
		self.assertEqual(gear.strength, 5)
		self.assertEqual(gear.int, 1)
		self.assertEqual(gear.intelligence, 1)
		self.assertEqual(gear.per, 3)
		self.assertEqual(gear.perception, 3)
		self.assertEqual(gear.con, 0)
		self.assertEqual(gear.constitution, 0)
		self.assertFalse(gear.twoHanded)
		self.assertFalse(gear.last)
		self.assertIsNone(gear.gearSet)

		gear = content.gear('dragonstooth')
		self.assertEqual(gear.key, 'dragonstooth')
		self.assertTrue(gear.is_special)
		self.assertEqual(gear.klass, 'special')
		self.assertEqual(gear.class_name, 'rogue')
		self.assertEqual(gear.specialClass, 'rogue')
		self.assertEqual(gear.event.start, datetime.date(2020, 1, 1))
		self.assertEqual(gear.event.end, datetime.date(2020, 1, 31))
		self.assertFalse(gear.twoHanded)
		self.assertTrue(gear.last)
		self.assertEqual(gear.gearSet, 'Nanoweapons')

		gear = content.gear('mysterykatana')
		self.assertEqual(gear.key, 'mysterykatana')
		self.assertFalse(gear.is_special)
		self.assertEqual(gear.klass, 'mystery')
		self.assertEqual(gear.class_name, 'mystery')
		self.assertEqual(gear.mystery, '202012')
		self.assertTrue(gear.twoHanded)
		self.assertFalse(gear.last)
		self.assertIsNone(gear.gearSet)
	def should_get_gear_from_tree(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		gear = content.gear_tree('weapon', 'rogue', 'katana')
		self.assertEqual(gear.key, 'ninja_katana')
	def should_get_mystery_sets(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content

		mystery = content.mystery('202012')
		self.assertEqual(mystery.key, '202012')
		self.assertEqual(mystery.start, datetime.date(2020, 12, 1))
		self.assertEqual(mystery.end, datetime.date(2020, 12, 31))
		self.assertEqual(mystery.text, 'Mystery Ninja')
		self.assertEqual(mystery.class_name, 'set_mystery_202012')
		gear = mystery.items()[0]
		self.assertEqual(gear.key, 'ninja_katana')
