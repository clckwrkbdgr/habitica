import unittest, unittest.mock
unittest.defaultTestLoader.testMethodPrefix = 'should'
from collections import namedtuple
from .. import core, api

class MockRequest:
	def __init__(self, method, path, response, cached=False):
		self.method = method
		self.path = path
		self.response = api.dotdict(response) if type(response) is dict else response
		self.params = None
		self.body = None
		self.cached = cached

class MockAPI:
	""" /content call is cached. """
	def __init__(self, *requests):
		self.base_url = 'http://localhost'
		self.requests = list(requests)
		self.responses = []
		self.cache = [
			MockRequest('get', ['content'], {'data': {'pets': '...'}}, cached=True),
			]
	def cached(self, *args, **kwargs):
		return self
	def _perform_request(self, method, path, params=None, body=None):
		for _ in self.cache:
			if _.method == method and list(_.path) == list(path):
				return _.response

		request = None
		for _ in self.requests:
			if _.method == method and list(_.path) == list(path):
				request = _
				break
		assert request is not None, "Expected request is not found in mock request chain: {0} /{1}".format(method.upper(), '/'.join(path))
		self.requests.remove(request)
		request.params = params
		request.body = body
		self.responses.append(request)
		if request.cached:
			self.cache.append(request)
		return request.response
	def get(self, *path, **params):
		return self._perform_request('get', path, params=params)
	def post(self, *path, _body=None, **params):
		return self._perform_request('post', path, params=params, body=_body)
	def put(self, *path, _body=None, **params):
		return self._perform_request('put', path, params=params, body=_body)
	def delete(self, *path, **params):
		return self._perform_request('delete', path, params=params)

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
			MockRequest('get', ['user'], {'data': {'name': '...'}}),
			))
		user = habitica.user()
	def should_get_groups(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [
				{'name' : 'Party'},
				{'name' : 'My Guild'},
				]}),
			))
		groups = habitica.groups(core.Group.PARTY, core.Group.GUILDS)
		self.assertEqual(len(groups), 2)
		self.assertEqual(groups[0].name, 'Party')
		self.assertEqual(groups[1].name, 'My Guild')

class TestChallenges(unittest.TestCase):
	def _challenge(self):
		return MockRequest('get', ['challenges', 'groups', 'group1'], {'data': [{
			'id' : 'chlng1',
			'name' : 'Create Habitica API tool',
			'shortName' : 'HabiticaAPI',
			'summary' : 'You have to create Habitica API tool',
			'createdAt' : 1600000000,
			'updatedAt' : 1600000000,
			'prize' : 4,
			'memberCount' : 2,
			'official' : False,
			'leader' : 'person1',
			'group' : {
				'id': 'group1',
				'name': 'Party',
				},
			'tasksOrder' : {
				'rewards' : ['reward1'],
				'todos' : ['todo1'],
				'dailys' : ['daily1'],
				'habits' : ['habit1'],
				},
			}]})
	def should_fetch_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('get', ['tasks', 'reward1'], {'data': {
				'text' : 'Use API tool',
				}}),
			MockRequest('get', ['tasks', 'todo1'], {'data': {
				'text' : 'Complete API tool',
				}}),
			MockRequest('get', ['tasks', 'daily1'], {'data': {
				'text' : 'Add feature',
				}}),
			MockRequest('get', ['tasks', 'habit1'], {'data': {
				'text' : 'Write better code',
				}}),
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
		self.assertEqual(challenge.leader(), 'person1')

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
	def should_get_challenge_data_as_csv(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('get', ['challenges', 'chlng1', 'export', 'csv'], 'AS CSV'),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		self.assertEqual(challenge.as_csv(), 'AS CSV')
	def should_clone_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('post', ['challenges', 'chlng1', 'clone'], {'challenge': {
				'id' : 'chlng2',
				'name' : 'Create Habitica API tool',
				'shortName' : 'HabiticaAPI',
				}})
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge = challenge.clone()
		self.assertEqual(challenge.id, 'chlng2')
		self.assertEqual(challenge.name, 'Create Habitica API tool')
		self.assertEqual(challenge.shortName, 'HabiticaAPI')
	def should_update_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('put', ['challenges', 'chlng1'], {'data': {
				'id' : 'chlng1',
				'name' : 'Develop Habitica API tool',
				'shortName' : 'API',
				'summary' : 'Go and create Habitica API tool',
				}})
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
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('post', ['challenges', 'chlng1', 'join'], {'data': {
					'id' : 'chlng1',
					'memberCount' : 3,
					}}),
			MockRequest('post', ['challenges', 'chlng1', 'leave'], {'data': {
					}}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge.join()
		self.assertEqual(challenge.memberCount, 3)
		challenge.leave()
		self.assertEqual(challenge.api.responses[-1].path[-1], 'leave')
	def should_select_winner(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('post', ['challenges', 'chlng1', 'selectWinner', 'person1'], {'data': {
					}}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		Person = namedtuple('Person', 'id name')
		challenge.selectWinner(Person('person1', 'Name'))
		self.assertEqual(challenge.api.responses[-1].path[-2:], ['selectWinner', 'person1'])
	def should_delete_challenge(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			self._challenge(),
			MockRequest('delete', ['challenges', 'chlng1'], {'data': {
					}}),
			))
		party = habitica.groups(core.Group.PARTY)[0]
		challenge = party.challenges()[0]
		challenge.delete()
		self.assertEqual(challenge.api.responses[-1].method, 'delete')
		self.assertEqual(challenge.api.responses[-1].path[-1], 'chlng1')

class TestChat(unittest.TestCase):
	def should_fetch_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('get', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					},{
					'id' : 'chat2',
					'user' : 'person2',
					'timestamp' : 1600001000,
					'text' : 'Hello back',
					}]}),
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
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('get', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat', 'chat1', 'flag'], {'data': {
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					'flagged' : True,
					}}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.flag(comment='Yazaban!')
		self.assertTrue(message._data['flagged'])
	def should_clear_message_from_flags(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('get', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat', 'chat1', 'clearflags'], {'data': {
					}}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.clearflags()
	def should_like_message(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('get', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat', 'chat1', 'like'], {'data': {
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					'liked' : 1,
					}}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		message = party.chat()[0]
		message.like()
		self.assertEqual(message._data['liked'], 1)
	def should_mark_messages_as_read(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat', 'seen'], {'data': [
					]}),
			))

		party = habitica.groups(core.Group.PARTY)[0]
		party.chat.mark_as_read()
	def should_delete_messages(self):
		habitica = core.Habitica(_api=MockAPI(
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('delete', ['groups', 'group1', 'chat', 'chat1'], {'data': [{
					}]}),
			MockRequest('get', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					}]}),
			MockRequest('delete', ['groups', 'group1', 'chat', 'chat1'], {'data': [{
					'id' : 'chat2',
					'user' : 'person2',
					'timestamp' : 1600001000,
					'text' : 'Hello back',
					}]}),
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
			MockRequest('get', ['groups'], {'data': [{
					'name' : 'Party',
					'id' : 'group1',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					}]}),
			MockRequest('post', ['groups', 'group1', 'chat'], {'data': [{
					'id' : 'chat1',
					'user' : 'person1',
					'timestamp' : 1600000000,
					'text' : 'Hello',
					},{
					'id' : 'chat1.2',
					'user' : 'person1',
					'timestamp' : 1600000400,
					'text' : 'Hey?',
					},{
					'id' : 'chat2',
					'user' : 'person2',
					'timestamp' : 1600001000,
					'text' : 'Hello back',
					}]}),
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
