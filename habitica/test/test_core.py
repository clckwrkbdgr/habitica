import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
import datetime
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
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			))
		groups = habitica.groups(core.Group.PARTY, core.Group.GUILDS)
		self.assertEqual(len(groups), 2)
		self.assertEqual(groups[0].name, 'Party')
		self.assertEqual(groups[0].type, 'party')
		self.assertEqual(groups[0].privacy, 'private')
		self.assertEqual(groups[1].name, 'My Guild')
		self.assertEqual(groups[1].type, 'guild')
		self.assertEqual(groups[1].privacy, 'public')
	def should_paginate_list_of_groups(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS_PAGE_1),
			))
		groups = habitica.groups(core.Group.PARTY, core.Group.GUILDS, page=1)
		self.assertEqual(len(groups), 1)
		self.assertEqual(groups[0].name, 'My Guild')
		self.assertEqual(groups[0].type, 'guild')
		self.assertEqual(groups[0].privacy, 'public')
	def should_run_cron(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('post', ['cron'], {}),
			))
		habitica.run_cron()
	def should_get_tavern(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups', 'habitrpg'], MockData.TAVERN),
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
			MockDataRequest('get', ['members', 'member1'], MockData.MEMBERS['member1']),
			))
		member = habitica.member('member1')
		self.assertEqual(member.name, 'John Doe')
		self.assertEqual(member.party().id, 'party1')
		self.assertEqual(member.inbox, {'not':'explained'})
		self.assertEqual(member.preferences, {'not':'explained'})
		self.assertEqual(member.stats, {'not':'explained'})
		self.assertEqual(member.items, {'not':'explained'})
		self.assertEqual(list(member.achievements().basic)[0].title, 'Sign Up')
		self.assertEqual(member.auth, {'not':'explained'})
	def should_transfer_gems_to_a_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['members', 'member1'], MockData.MEMBERS['member1']),
			MockRequest('get', ['members', 'member1', 'objections', 'transfer-gems'], {'data': [
				{'not':'explained'},
				]}),
			MockRequest('get', ['members', 'member1', 'objections', 'transfer-gems'], {'data': [
				]}),
			MockRequest('post', ['members', 'transfer-gems'], {'data': [ ]}),
			))
		member = habitica.member('member1')
		with self.assertRaises(RuntimeError):
			habitica.transfer_gems(member, Price(1, 'gems'), 'Here you go.')
		habitica.transfer_gems(member, Price(1, 'gems'), 'Here you go.')
	def should_send_private_message_to_a_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['members', 'member1'], {'data': {
				'_id' : 'member1',
				}}),
			MockRequest('get', ['members', 'member1', 'objections', 'send-private-message'], {'data': [
				{'not':'explained'},
				]}),
			MockRequest('get', ['members', 'member1', 'objections', 'send-private-message'], {'data': [
				]}),
			MockRequest('post', ['members', 'send-private-message'], {'data': {
				'not':'explained',
				}}),
			))
		member = habitica.member('member1')
		with self.assertRaises(RuntimeError):
			habitica.send_private_message(member, 'Incoming message.')
		message = habitica.send_private_message(member, 'Incoming message.')
		self.assertEqual(message._data, {'not':'explained'})

class TestChallenges(unittest.TestCase):
	def _challenge(self, path=('groups', 'group1')):
		return MockRequest('get', ['challenges'] + list(path), MockData.CHALLENGES)
	def should_fetch_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['members', 'person1'], MockData.MEMBERS['member1']),
			MockDataRequest('get', ['tasks', 'reward1'], MockData.REWARDS['reward1']),
			MockDataRequest('get', ['tasks', 'todo1'], MockData.TODOS['todo1']),
			MockDataRequest('get', ['tasks', 'daily1'], MockData.DAILIES['daily1']),
			MockDataRequest('get', ['tasks', 'habit1'], MockData.HABIS['habit1']),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		self.assertEqual(challenge.id, 'chlng1')
		self.assertEqual(challenge.name, 'Create Habitica API tool')
		self.assertEqual(challenge.shortName, 'HabiticaAPI')
		self.assertEqual(challenge.createdAt, 1600000000)
		self.assertEqual(challenge.updatedAt, 1600000000)
		self.assertEqual(challenge.prize, 4)
		self.assertEqual(challenge.memberCount, 2)
		self.assertFalse(challenge.official)
		self.assertEqual(challenge.leader().id, 'person1')

		group = challenge.group()
		self.assertEqual(group.id, party.id)
		self.assertEqual(group.name, party.name)

		rewards = challenge.rewards()
		self.assertEqual(rewards[0].text, 'Use API tool')
		todos = challenge.todos()
		self.assertEqual(todos[0].text, 'Complete API tool')
		dailies = challenge.dailies()
		self.assertEqual(dailies[0].text, 'Add feature')
		habits = challenge.habits()
		self.assertEqual(habits[0].text, 'Write better code')
	def should_fetch_user_challenges(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			self._challenge(path=('user',)),
			MockDataRequest('get', ['members', 'person1'], MockData.MEMBERS['member1']),
			))
		user = habitica.user()
		challenge = user.challenges()[0]
		self.assertEqual(challenge.id, 'chlng1')
		self.assertEqual(challenge.name, 'Create Habitica API tool')
		self.assertEqual(challenge.leader().id, 'person1')
	def should_get_challenge_data_as_csv(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockRequest('get', ['challenges', 'chlng1', 'export', 'csv'], 'AS CSV'),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		self.assertEqual(challenge.as_csv(), 'AS CSV')
	def should_create_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['challenges'], MockData.NEW_CHALLENGE),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.create_challenge(
				'Create Habitica API tool', 'HabiticaAPI',
				summary='You have to create Habitica API tool',
				description='You have to create Habitica API tool',
				prize=4,
				)
		self.assertEqual(challenge.id, 'chlng1')
	def should_clone_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockRequest('post', ['challenges', 'chlng1', 'clone'], {'challenge': MockData.NEW_CHALLENGE})
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge = challenge.clone()
		self.assertEqual(challenge.id, 'chlng2')
		self.assertEqual(challenge.name, 'Create Habitica API tool')
		self.assertEqual(challenge.shortName, 'HabiticaAPI')
	def should_update_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('put', ['challenges', 'chlng1'], MockData.UPDATED_CHALLENGE)
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge.update()
		self.assertEqual(challenge.name, 'Create Habitica API tool')
		self.assertEqual(challenge.shortName, 'HabiticaAPI')
		self.assertEqual(challenge.summary, 'You have to create Habitica API tool')
		challenge.update(
				name = 'Develop Habitica API tool',
				summary = 'API',
				description = 'Go and create Habitica API tool',
				)
		self.assertEqual(challenge.name, 'Develop Habitica API tool')
		self.assertEqual(challenge.shortName, 'API')
		self.assertEqual(challenge.summary, 'Go and create Habitica API tool')
	def should_join_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['challenges', 'chlng1', 'join'], dict(MockData.CHALLENGES[0], memberCount=3)),
			MockDataRequest('post', ['challenges', 'chlng1', 'leave'], {}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge.join()
		self.assertEqual(challenge.memberCount, 3)
		challenge.leave()
		self.assertEqual(challenge.api.responses[-1].path[-1], 'leave')
	def should_select_winner(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('post', ['challenges', 'chlng1', 'selectWinner', 'person1'], {}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		Person = namedtuple('Person', 'id name')
		challenge.selectWinner(Person('person1', 'Name'))
		self.assertEqual(challenge.api.responses[-1].path[-2:], ['selectWinner', 'person1'])
	def should_delete_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockDate.GROUPS),
			self._challenge(),
			MockDataRequest('delete', ['challenges', 'chlng1'], {}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge.delete()
		self.assertEqual(challenge.api.responses[-1].method, 'delete')
		self.assertEqual(challenge.api.responses[-1].path[-1], 'chlng1')
	def should_get_member(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['challenges', 'chlng1', 'members', 'member1'], MockData.MEMBERS['member1']),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		member = challenge.member('member1')
		self.assertEqual(member.id, 'member1')
		self.assertEqual(member.name, 'John Doe')
		tasks = member.tasks()
		self.assertEqual(tasks[0].id, 'task1')
		self.assertEqual(tasks[0].text, 'Do a barrel roll')
	def should_get_members_for_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			self._challenge(),
			MockDataRequest('get', ['challenges', 'chlng1', 'members'], [
				MockData.MEMBERS['member{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['challenges', 'chlng1', 'members'], [
				MockData.MEMBERS['member31']
				]),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		members = list(challenge.members())
		self.assertEqual(members[0].id, 'member1')
		self.assertEqual(members[30].id, 'member31')

class TestChat(unittest.TestCase):
	def should_fetch_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'chat'], MockData.PARTY_CHAT),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		messages = party.chat()
		self.assertEqual(messages[0].id, 'chat1')
		self.assertEqual(messages[0].timestamp, 1600000000)
		self.assertEqual(messages[0].user, 'person1')
		self.assertEqual(messages[0].text, 'Hello')
		self.assertEqual(messages[1].id, 'chat2')
		self.assertEqual(messages[1].timestamp, 1600001000)
		self.assertEqual(messages[1].user, 'person2')
		self.assertEqual(messages[1].text, 'Hello back')
	def should_flag_message(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'chat'], MockData.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'group1', 'chat', 'chat1', 'flag'], MockData.PARTY_CHAT_FLAGGED),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.flag(comment='Yazaban!')
		self.assertTrue(message._data['flagged'])
	def should_clear_message_from_flags(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'chat'], MockData.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'group1', 'chat', 'chat1', 'clearflags'], {}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.clearflags()
	def should_like_message(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'chat'], MockDate.PARTY_CHAT),
			MockDataRequest('post', ['groups', 'group1', 'chat', 'chat1', 'like'], MockData.PARTY_CHAT_LIKEF),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.like()
		self.assertEqual(message._data['liked'], 1)
	def should_mark_messages_as_read(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'chat', 'seen'], {}),
			MockDataRequest('post', ['groups', 'group1', 'chat', 'seen'], {}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		party.chat.mark_as_read()
		party.mark_chat_as_read()
	def should_delete_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('delete', ['groups', 'group1', 'chat', 'chat1'], {}),
			MockDataRequest('get', ['groups', 'group1', 'chat'], [
				MockData.PARTY_CHAT[0]
				]),
			MockRequest('delete', ['groups', 'group1', 'chat', 'chat1'], [
				MockData.PARTY_CHAT[1]
				]),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		chat = party.chat
		chat.delete(core.ChatMessage(_data={'id':'chat1'}))
		self.assertFalse(chat._entries)
		self.assertEqual(chat.messages()[0].id, 'chat1')
		self.assertEqual(chat.messages()[0].timestamp, 1600000000)
		self.assertEqual(chat.messages()[0].user, 'person1')
		self.assertEqual(chat.messages()[0].text, 'Hello')
		chat.delete(core.ChatMessage(_data={'id':'chat1'}))
		self.assertEqual(chat.messages()[0].id, 'chat2')
		self.assertEqual(chat.messages()[0].timestamp, 1600001000)
		self.assertEqual(chat.messages()[0].user, 'person2')
		self.assertEqual(chat.messages()[0].text, 'Hello back')
	def should_post_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'chat'], [MockData.PARTY_CHAT[0]]),
			MockDataRequest('post', ['groups', 'group1', 'chat'], MockData.LONG_CHAT),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		chat = party.chat
		chat.post('Hello')
		self.assertEqual(chat.messages()[0].id, 'chat1')
		self.assertEqual(chat.messages()[0].timestamp, 1600000000)
		self.assertEqual(chat.messages()[0].user, 'person1')
		self.assertEqual(chat.messages()[0].text, 'Hello')
		chat.post('Hey?')
		self.assertEqual(chat.messages()[2].id, 'chat2')
		self.assertEqual(chat.messages()[2].timestamp, 1600001000)
		self.assertEqual(chat.messages()[2].user, 'person2')
		self.assertEqual(chat.messages()[2].text, 'Hello back')

class TestGroup(unittest.TestCase):
	def should_fetch_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'add-manager'], {}),
			MockDataRequest('post', ['groups', 'group1', 'remove-manager'], {}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		party.add_manager(core.Member(_data={'id':'member1'}))
		party.remove_manager(core.Member(_data={'id':'member1'}))
	def should_create_group_plan(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups', 'create-plan'], MockData.NEW_PLAN),
			))
		group = habitica.create_plan()
		self.assertEqual(group.id, 'group1')
		self.assertEqual(group.name, 'Party')
	def should_create_guild(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups'], MockData.NEW_GUILD),
			))
		group = habitica.create_guild('My Guild', public=True)
		self.assertEqual(group.id, 'group1')
		self.assertEqual(group.name, 'My Guild')
		self.assertTrue(group.is_public)
	def should_create_party(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('post', ['groups'], MockData.NEW_PARTY),
			MockDataRequest('get', ['members', 'user1'], MockData.MEMBERS['member1']),
			))
		group = habitica.create_party('My Party')
		self.assertTrue(type(group) is core.Party)
		self.assertEqual(group.id, 'group1')
		self.assertEqual(group.name, 'My Party')
		self.assertFalse(group.is_public)
		self.assertEqual(group.leader().id, 'user1')
		self.assertEqual(group.memberCount, 1)
		self.assertEqual(group.challengeCount, 0)
		self.assertEqual(group.balance, Price(1, 'gems'))
		self.assertEqual(group.logo, 'foo')
		self.assertEqual(group.leaderMessage, 'bar')
	def should_invite_users(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'invite'], {}),
			MockDataRequest('post', ['groups', 'group1', 'reject-invite'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		with self.assertRaises(ValueError):
			group.invite('neither Email nor Member')
		group.invite(
				core.Email('user@example.org'),
				core.Email('another@example.org', 'A Person'),
				habitica.child(core.Member, {'id':'user1'}),
				)

		habitica.user.reject_invite(group)
	def should_join_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'join'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		habitica.user.join(group)
	def should_leave_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'leave'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		habitica.user.leave(group, keep_tasks=False, leave_challenges=False)
	def should_remove_members_from_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('post', ['groups', 'group1', 'removeMember', 'member1'], {}),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		group.removeMember(habitica.child(core.Member, {'id':'member1'}))
	def should_get_invites_for_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'invites'], [
				MockData.MEMBERS['member{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['groups', 'group1', 'invites'], [
				MockData.MEMBERS['member31'],
				]),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		members = list(group.all_invites())
		self.assertEqual(members[0].id, 'member1')
		self.assertEqual(members[30].id, 'member31')
	def should_get_members_for_a_group(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['groups'], MockData.GROUPS),
			MockDataRequest('get', ['groups', 'group1', 'members'], [
				MockData.MEMBERS['member{0}'.format(i)] for i in range(1, 31)
				]),
			MockDataRequest('get', ['groups', 'group1', 'members'], [
				MockData.MEMBERS['member31'],
				]),
			))
		group = habitica.groups(core.Group.GUILDS)[0]
		members = list(group.members())
		self.assertEqual(members[0].id, 'member1')
		self.assertEqual(members[30].id, 'member31')

class TestUser(unittest.TestCase):
	def _user_data(self, stats=None, **kwargs):
		result = dict(MockData.USER, **kwargs)
		result['stats'] = dict(result['stats'], stats)
		return result
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
	def should_get_user_preferences(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(user.preferences.timezoneOffset, 180)
	def should_get_food_in_user_inventory(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(len(user.inventory.food), 2)
	def should_get_user_pet_and_mount(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			))
		user = habitica.user()
		self.assertEqual(user.inventory.pet.text, 'Fox')
		self.assertEqual(user.inventory.mount.text, 'Wolf')
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
	def should_get_user_avatar(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockRequest('get', ['export', 'avatar-USER-ID.html'], '<html/>'),
			))

		user = habitica.user()
		self.assertEqual(user.avatar(), '<html/>')
	def should_get_user_group_plans(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], self._user_data()),
			MockDataRequest('get', ['group-plans'], [MockData.NEW_PLAN]),
			))

		user = habitica.user()
		groups = user.group_plans()
		self.assertEqual(groups[0].id, 'group1')
	def should_get_member_achievements(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['members', 'member1'], MockData.MEMBERS['member1']),
			MockDataRequest('get', ['members', 'member1', 'achievements'], MockData.ACHIEVEMENTS),
			))

		member = habitica.member('member1')
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

class TestQuest(unittest.TestCase):
	def should_show_progress_of_collection_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'party'], MockData.PARTY),
			))
		party = habitica.user().party()
		quest = party.quest
		self.assertTrue(quest.active)
		self.assertEqual(quest.key, 'collectionquest')
		self.assertEqual(quest.title, 'Collect N items')
		self.assertEqual(quest.progress, 10)
		self.assertEqual(quest.max_progress, 30)
	def should_show_progress_of_boss_quest(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['groups', 'myguild'], MockData.GROUPS[1]),
			))
		party = habitica.user().party()
		quest = party.quest
		self.assertTrue(quest.active)
		self.assertEqual(quest.key, 'bossquest')
		self.assertEqual(quest.title, 'Defeat the Boss')
		self.assertEqual(quest.progress, 20)
		self.assertEqual(quest.max_progress, 500)

class TestRewards(unittest.TestCase):
	def should_get_user_rewards(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_REWARDS),
			))
		user = habitica.user()
		rewards = user.rewards()
		self.assertEqual(rewards[0].id, 'reward1')
		self.assertEqual(rewards[0].text, 'Eat')
		self.assertEqual(rewards[1].id, 'reward2')
		self.assertEqual(rewards[1].text, 'Sleep')
	def should_buy_reward(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_REWARDS),
			MockDataRequest('post', ['tasks', 'reward1', 'score', 'up'], {}),
			))
		user = habitica.user()
		rewards = user.rewards()
		user.buy(rewards[0])

class TestHabits(unittest.TestCase):
	def should_get_list_of_user_habits(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_HABITS),
			))
		user = habitica.user()
		habits = user.habits()
		self.assertEqual(habits[0].id, 'habit1')
		self.assertEqual(habits[0].text, 'Keep calm')
		self.assertEqual(habits[0].notes, 'And carry on')
		self.assertEqual(habits[0].value, 5.1)
		self.assertEqual(habits[0].color, core.Task.LIGHT_BLUE)
		self.assertTrue(habits[0].can_score_up)
		self.assertFalse(habits[0].can_score_down)
	def should_separate_habits_by_color(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_HABITS),
			))
		user = habitica.user()
		habits = user.habits()
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
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_HABITS),
			MockDataRequest('post', ['tasks', 'habit1', 'score', 'up'], {
				'delta' : 1.1,
				}),
			))
		user = habitica.user()
		habits = user.habits()
		habits[0].up()
		self.assertAlmostEqual(habits[0].value, 6.2)
		with self.assertRaises(core.CannotScoreUp) as e:
			habits[1].up()
		self.assertEqual(str(e.exception), "Habit 'Carry on' cannot be incremented")
	def should_score_habits_down(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_HABITS),
			MockDataRequest('post', ['tasks', 'habit1', 'score', 'down'], {
				'delta' : -1.1,
				}),
			))
		user = habitica.user()
		habits = user.habits()
		habits[0].down()
		self.assertAlmostEqual(habits[0].value, 4.0)
		with self.assertRaises(core.CannotScoreDown) as e:
			habits[1].down()
		self.assertEqual(str(e.exception), "Habit 'Carry on' cannot be decremented")

class TestDailies(unittest.TestCase):
	def should_get_list_of_user_dailies(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_DAILIES),
			))
		user = habitica.user()
		dailies = user.dailies()
		self.assertEqual(dailies[0].id, 'daily1')
		self.assertEqual(dailies[0].text, 'Rise')
		self.assertEqual(dailies[0].notes, 'And shine')
		self.assertFalse(dailies[0].is_completed)

		checklist = dailies[0].checklist
		self.assertEqual(checklist[0].id, 'subdaily1')
		self.assertEqual(checklist[0].text, 'Rise')
		self.assertTrue(checklist[0].is_completed)
		self.assertEqual(checklist[0].parent.id, 'daily1')

		self.assertEqual(dailies[0][1].id, 'subdaily2')
		self.assertEqual(dailies[0][1].text, 'Shine')
		self.assertFalse(dailies[0][1].is_completed)
	def should_detect_due_dailies(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_DAILIES),
			))
		user = habitica.user()
		dailies = user.dailies()

		self.assertFalse(dailies[0].is_due(today=timeutils.parse_isodate('2016-11-09 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[0].is_due(today=timeutils.parse_isodate('2016-11-10 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(dailies[0].is_due(today=timeutils.parse_isodate('2016-11-11 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[0].is_due(today=timeutils.parse_isodate('2016-11-12 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(dailies[0].is_due(today=timeutils.parse_isodate('2016-11-23 16:51:15.930842'), timezoneOffset=-120))

		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-09 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-10 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-11 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-12 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-13 16:51:15.930842'), timezoneOffset=-120))
		self.assertTrue(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-14 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-15 16:51:15.930842'), timezoneOffset=-120))
		self.assertFalse(dailies[1].is_due(today=timeutils.parse_isodate('2016-11-16 16:51:15.930842'), timezoneOffset=-120))
	def should_complete_daily(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_DAILIES),
			MockDataRequest('post', ['tasks', 'daily1', 'score', 'up'], {}),
			MockDataRequest('post', ['tasks', 'daily1', 'score', 'down'], {}),
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
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_DAILIES),
			MockDataRequest('post', ['tasks', 'daily1', 'checklist', 'subdaily1', 'score'], {}),
			MockDataRequest('post', ['tasks', 'daily1', 'checklist', 'subdaily2', 'score'], {}),
			))
		user = habitica.user()
		dailies = user.dailies()
		self.assertFalse(dailies[0].is_completed)

		dailies[0][0].complete()
		self.assertTrue(dailies[0][0].is_completed)
		dailies[0][0].undo()
		self.assertFalse(dailies[0][0].is_completed)

		dailies[0][1].undo()
		self.assertFalse(dailies[0][1].is_completed)
		dailies[0][1].complete()
		self.assertTrue(dailies[0][1].is_completed)

class TestTodos(unittest.TestCase):
	def should_get_list_of_user_todos(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_TODOS),
			))
		user = habitica.user()
		todos = user.todos()
		self.assertEqual(todos[0].id, 'todo1')
		self.assertEqual(todos[0].text, 'Rise')
		self.assertEqual(todos[0].notes, 'And shine')
		self.assertFalse(todos[0].is_completed)

		checklist = todos[0].checklist
		self.assertEqual(checklist[0].id, 'subtodo1')
		self.assertEqual(checklist[0].text, 'Rise')
		self.assertTrue(checklist[0].is_completed)
		self.assertEqual(checklist[0].parent.id, 'todo1')

		self.assertEqual(todos[0][1].id, 'subtodo2')
		self.assertEqual(todos[0][1].text, 'Shine')
		self.assertFalse(todos[0][1].is_completed)
	def should_complete_todo(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_TODOS),
			MockDataRequest('post', ['tasks', 'todo1', 'score', 'up'], {}),
			MockDataRequest('post', ['tasks', 'todo1', 'score', 'down'], {}),
			))
		user = habitica.user()
		todos = user.todos()
		self.assertFalse(todos[0].is_completed)

		todos[0].complete()
		self.assertTrue(todos[0].is_completed)

		todos[0].undo()
		self.assertFalse(todos[0].is_completed)
	def should_complete_check_items(self):
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_TODOS),
			MockDataRequest('post', ['tasks', 'todo1', 'checklist', 'subtodo1', 'score'], {}),
			MockDataRequest('post', ['tasks', 'todo1', 'checklist', 'subtodo2', 'score'], {}),
			))
		user = habitica.user()
		todos = user.todos()
		self.assertFalse(todos[0].is_completed)

		todos[0][0].complete()
		self.assertTrue(todos[0][0].is_completed)
		todos[0][0].undo()
		self.assertFalse(todos[0][0].is_completed)

		todos[0][1].undo()
		self.assertFalse(todos[0][1].is_completed)
		todos[0][1].complete()
		self.assertTrue(todos[0][1].is_completed)

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
		habitica = core.Habitica(_api=MockAPI(
			MockDataRequest('get', ['user'], MockData.USER),
			MockDataRequest('post', ['user', 'class', 'cast', 'stealth'], {}),
			MockDataRequest('get', ['tasks', 'user'], MockData.USER_TODOS),
			MockDataRequest('post', ['user', 'class', 'cast', 'backStab'], {}),
			))
		user = habitica.user()
		spell = user.get_spell('stealth')
		user.cast(spell)
		target = user.todos()[0]
		spell = user.get_spell('backStab')
		user.cast(spell, target)

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

		food = content.food()[0]
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
		self.assertEqual(backgrounds[0].key, 'fall')
		self.assertEqual(backgrounds[0].text, 'Fall')
		self.assertEqual(backgrounds[0].notes, "Summer's End")
		self.assertEqual(backgrounds[0].price, Price(7, 'gems'))
		self.assertEqual(backgrounds[0].set_name, 'Fall')

		backgrounds = sorted(content.get_background_set(2020), key=lambda _:_.key)
		self.assertEqual(backgrounds[0].key, 'blizzard')
		self.assertEqual(backgrounds[1].key, 'fall')

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
		quest = content.get_quest('bossquest')

		self.assertEqual(quest.key, 'bossquest')
		self.assertEqual(quest.text, 'Defeat the Boss')
		self.assertEqual(quest.notes, 'Additional notes')
		self.assertTrue(quest.userCanOwn)
		self.assertEqual(quest.category, 'unlockable')

		condition = quest.unlockCondition
		self.assertEqual(condition.text, 'Swipe to unlock')
		self.assertEqual(condition.condition, 'login')
		self.assertEqual(condition.incentiveThreshold, 3)

		self.assertEqual(quest.level, 33)
		self.assertIsNone(quest.goldValue)
		self.assertEqual(quest.group, 'questgroup1')
		self.assertIsNone(quest.previous)
		self.assertEqual(quest.completion, 'You defeated the Boss!')
		self.assertIsNone(quest.completionChat)
		self.assertEqual(quest.colors, {})
		self.assertIsNone(quest.event)

		drop = quest.drop
		self.assertEqual(drop.unlock, '')
		self.assertEqual(drop.experience, 300)
		self.assertEqual(drop.gold, 10)
		items = drop.items
		self.assertEqual(items[0].key, 'collectionquest')
		self.assertEqual(items[0].text, 'Collect N items')
		self.assertEqual(items[0].type, 'quests')
		self.assertTrue(items[0].onlyOwner)
		self.assertEqual(items[0].get_content_entry().key, 'collectionquest')

		self.assertIsNone(quest.collect)
		boss = quest.boss
		self.assertEqual(boss.name, 'The Boss')
		self.assertEqual(boss.strength, 1)
		self.assertEqual(boss.defense, 0.5)
		self.assertEqual(boss.hp, 500)
		self.assertIsNone(boss.rage)
	def should_have_quest_with_collection(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		quest = content.get_quest('collectionquest')

		self.assertEqual(quest.key, 'collectionquest')
		self.assertEqual(quest.text, 'Collect N items')
		self.assertEqual(quest.notes, 'Additional notes')
		self.assertTrue(quest.userCanOwn)
		self.assertEqual(quest.category, 'pet')
		self.assertIsNone(quest.unlockCondition)
		self.assertEqual(quest.goldValue, Price(10, 'gold'))
		self.assertEqual(quest.group, 'questgroup1')
		self.assertEqual(quest.previous.key, 'bossquest')
		self.assertEqual(quest.completion, 'You collected N items!')
		self.assertIsNone(quest.completionChat)
		self.assertEqual(quest.colors, {})
		self.assertIsNone(quest.event)

		drop = quest.drop
		self.assertEqual(drop.unlock, '')
		self.assertEqual(drop.experience, 500)
		self.assertEqual(drop.gold, 100)
		items = drop.items
		self.assertEqual(items[0].key, 'fox')
		self.assertEqual(items[0].text, 'Fox Egg')
		self.assertEqual(items[0].type, 'dropEggs')
		self.assertFalse(items[0].onlyOwner)
		self.assertEqual(items[0].get_content_entry().key, 'fox')

		self.assertIsNone(quest.boss)
		collect = quest.collect
		self.assertEqual(set(collect.names), {'fun', 'games'})
		self.assertEqual(collect.get_item('fun'), ('fun', 'Fun', 10))
		self.assertEqual(collect.get_item('games'), ('games', 'Games', 20))
		collect_items = sorted(collect.items(), key=lambda _:_[0])
		self.assertEqual(collect_items[0], ('fun', 'Fun', 10))
		self.assertEqual(collect_items[1], ('games', 'Games', 20))
		self.assertEqual(collect.total, 30)
	def should_have_world_quest(self):
		habitica = core.Habitica(_api=MockAPI())
		content = habitica.content
		quest = content.get_quest('worldquest')

		self.assertEqual(quest.key, 'worldquest')
		self.assertEqual(quest.text, 'Protect the World')
		self.assertEqual(quest.notes, 'Additional notes')
		self.assertFalse(quest.userCanOwn)
		self.assertEqual(quest.category, 'world')
		self.assertIsNone(quest.goldValue)
		self.assertIsNone(quest.group)
		self.assertIsNone(quest.previous)
		self.assertEqual(quest.completion, 'You protected the World!')
		self.assertEqual(quest.completionChat, 'You protected the World!')
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
		self.assertEqual(boss.name, 'The World Boss')
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

		gear = content.gear('daikatana')
		self.assertEqual(gear.key, 'daikatana')
		self.assertTrue(gear.is_special)
		self.assertEqual(gear.klass, 'special')
		self.assertEqual(gear.class_name, 'rogue')
		self.assertEqual(gear.specialClass, 'rogue')
		self.assertEqual(gear.event.start, datetime.date(2020, 1, 1))
		self.assertEqual(gear.event.end, datetime.date(2020, 1, 31))
		self.assertFalse(gear.twoHanded)
		self.assertTrue(gear.last)
		self.assertEqual(gear.gearSet, 'DOOM')

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
