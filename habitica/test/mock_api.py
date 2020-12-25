import types
from .. import core, api

MockData = types.SimpleNamespace()

class MockRequest:
	def __init__(self, method, path, response, cached=False):
		self.method = method
		self.path = path
		self.response = api.dotdict(response) if type(response) is dict else response
		self.params = None
		self.body = None
		self.cached = cached

class MockDataRequest(MockRequest):
	def __init__(self, method, path, data, cached=False):
		super().__init__(method, path, {'data':data}, cached=cached)

class MockAPI:
	""" /content call is cached. """
	def __init__(self, *requests):
		self.base_url = 'http://localhost'
		self.requests = list(requests)
		self.responses = []
		self.cache = [
			MockRequest('get', ['content'], {'data': MockData.CONTENT_DATA}, cached=True),
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
		if request.cached: # pragma: no cover
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

#### DATABASE AND REQUESTS #####################################################

MockData.USER = {
		'id' : 'USER-ID',
		'stats' : {
			'class': 'rogue',
			'hp': 30.0,
			'maxHealth': 50.0,
			'lvl': 33,
			'exp': 1049.4,
			'toNextLevel': 51.6,
			'mp': 11.0,
			'maxMP': 55.0,
			'gp': 15.0,
			},
		'preferences' : {
			'timezoneOffset' : 180,
			},
		'items' : {
			'food' : [
				'Meat', 'Honey',
				],
			'currentPet' : 'fox',
			'currentMount' : 'wolf',
			},
		}

MockData.REWARDS = {
		'reward1' : {
			'text' : 'Use API tool',
			},
		'reward2' : {'id':'reward1', 'text':'Eat'},
		'reward3' : {'id':'reward2', 'text':'Sleep'},
		}
MockData.USER_REWARDS = [
		MockData.REWARDS['reward2'],
		MockData.REWARDS['reward3'],
		]

MockData.TODOS = {
		'todo1' : {
			'text' : 'Complete API tool',
			},
		}
MockData.USER_TODOS = [
		{
			'id':'todo1',
			'text':'Rise',
			'notes':'And shine',
			'completed':False,
			'checklist': [
				{
					'id':'subtodo1',
					'text':'Rise',
					'completed':True,
					},
				{
					'id':'subtodo2',
					'text':'Shine',
					'completed':False,
					},
				],
			},
		]

MockData.DAILIES = {
		'daily1' : {
			'text' : 'Add feature',
			},
		'daily2' : {
			'id':'daily1',
			'text':'Rise',
			'notes':'And shine',
			'completed':False,
			'checklist': [
				{
					'id':'subdaily1',
					'text':'Rise',
					'completed':True,
					},
				{
					'id':'subdaily2',
					'text':'Shine',
					'completed':False,
					},
				],
			},
		}
MockData.USER_DAILIES = [
		MockData.DAILIES['daily2'],
		{
			'id':'daily1',
			'text':'Rise',
			'frequency':'daily',
			'startDate':'2016-06-20T21:00:00.000Z',
			'everyX':12,
			},
		{
			'id':'daily2',
			'text':'Survive Monday',
			'frequency':'weekly',
			'repeat':{
				"m":True,
				"t":False,
				"w":False,
				"th":False,
				"f":False,
				"s":False,
				"su":False,
				},
			},
		]

MockData.HABITS = {
		'habit1' : {
			'text' : 'Write better code',
			},
		'habit2' : {
			'id':'habit1',
			'text':'Keep calm',
			'notes':'And carry on',
			'value':5.1,
			'up':True,
			'down':False,
			},
		}
MockData.USER_HABITS = [
		MockData.HABITS['habit2'],
		{
			'id':'habit2',
			'text':'Carry on',
			'value':5.1,
			'up':False,
			'down':False,
			},
		{ 'value':-50.1, },
		{ 'value':-15.4, },
		{ 'value':-5.6, },
		{ 'value':0.0, },
		{ 'value':1.1, },
		{ 'value':5.1, },
		{ 'value':15.1, },
		]

MockData.GROUPS = [
	{
		'name' : 'Party',
		'type' : 'party',
		'privacy' : 'private',
		'quest' : {
			'active' : True,
			'key' : 'collectionquest',
			'progress' : {
				'collect' : {
					'fun' : 7,
					'games' : 3,
					}
				},
			},
		},
	{
		'name' : 'My Guild',
		'type' : 'guild',
		'privacy' : 'public',
		'quest' : {
			'active' : True,
			'key' : 'bossquest',
			'progress': {
				'hp' : 20,
				},
			},
		},
	{
		'name' : 'Tavern',
		'type' : 'habitrpg',
		},
	]
MockData.GROUPS_PAGE_1 = MockData.GROUPS[:1]
MockData.PARTY = MockData.GROUPS[0]
MockData.TAVERN = MockData.GROUPS[-1]
MockData.NEW_PLAN = {
		'name' : 'Party',
		'id' : 'group1',
		}
MockData.NEW_GUILD = {
		'name' : 'My Guild',
		'id' : 'group1',
		'type' : 'guild',
		'privacy' : 'public',
		}
MockData.NEW_PARTY = {
		'name' : 'My Party',
		'id' : 'group1',
		'type' : 'party',
		'privacy' : 'private',
		'leader' : 'user1',
		'memberCount' : 1,
		'challengeCount' : 0,
		'balance' : 1,
		'logo' : "foo",
		'leaderMessage' : "bar",
		}

MockData.PARTY_CHAT = [
		{
			'id' : 'chat1',
			'user' : 'person1',
			'timestamp' : 1600000000,
			'text' : 'Hello',
			},
		{
			'id' : 'chat2',
			'user' : 'person2',
			'timestamp' : 1600001000,
			'text' : 'Hello back',
			}
		]
MockData.PARTY_CHAT_FLAGGED = {
		'id' : 'chat1',
		'user' : 'person1',
		'timestamp' : 1600000000,
		'text' : 'Hello',
		'flagged' : True,
		}
MockData.PARTY_CHAT_LIKED = {
		'id' : 'chat1',
		'user' : 'person1',
		'timestamp' : 1600000000,
		'text' : 'Hello',
		'liked' : 1,
		}
MockData.LONG_CHAT = [
		{
			'id' : 'chat1',
			'user' : 'person1',
			'timestamp' : 1600000000,
			'text' : 'Hello',
			},
		{
			'id' : 'chat1.2',
			'user' : 'person1',
			'timestamp' : 1600000400,
			'text' : 'Hey?',
			},
		{
			'id' : 'chat2',
			'user' : 'person2',
			'timestamp' : 1600001000,
			'text' : 'Hello back',
			}
		]

MockData.CHALLENGES = [
		{
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
			},
		]
MockData.NEW_CHALLENGE = {
		'id' : 'chlng2',
		'name' : 'Create Habitica API tool',
		'shortName' : 'HabiticaAPI',
		}
MockData.UPDATED_CHALLENGE = {
		'id' : 'chlng1',
		'name' : 'Develop Habitica API tool',
		'shortName' : 'API',
		'summary' : 'Go and create Habitica API tool',
		}

MockData.MEMBERS = {
		'member1' : {
			'_id' : 'member1',
			'profile' : {
				'name' : 'John Doe',
				},
			'party' : {
				'id' : 'party1',
				},
			'preferences' : {
				'not' : 'explained',
				},
			'inbox' : {
				'not' : 'explained',
				},
			'stats' : {
				'not' : 'explained',
				},
			'items' : {
				'not' : 'explained',
				},
			'tasks' : [
				{
					'id' : 'task1',
					'text' : 'Do a barrel roll',
					},
				],
			'achievements' : {
				'basic' : {
					'achievements' : {
						'signup' : {
							'title' : 'Sign Up',
							},
						},
					},
				'not' : 'explained',
				},
			'auth' : {
				'not' : 'explained',
				},
			},
		}
MockData.MEMBERS.update({
	'member{0}'.format(i):{
		'id' : 'member{0}'.format(i),
		}
	for i in range(1, 31+1)
	})
MockData.ACHIEVEMENTS = {
		'basic' : {
			'label' : 'Basic',
			'achievements' : {
				'signup' : {
					'title' : 'Sign Up',
					'text' : 'Sign Up with Habitica',
					'icon' : 'achievement-login',
					'earned' : True,
					'value' : 0,
					'index' : 60,
					'optionalCount': 0,
					},
				},
			}
		}

MockData.CONTENT_DATA = {
		'potion' : {
			'text' : 'Health Potion',
			'notes' : 'Heals 15 hp',
			'type' : 'potion',
			'key' : 'HealthPotion',
			'value' : 25,
			},
		'armoire' : {
			'text' : 'Enchanted Armoire',
			'type' : 'armoire',
			'key' : 'Armoire',
			'value' : 100,
			},
		'classes' : [
			'warrior',
			'rogue',
			'wizard',
			'healer',
			],
		'gearTypes' : [
			"headAccessory",
			"armor",
			"head",
			],
		'questEggs' : {
			'badger' : {
				'key':'badger',
				'text':'Badger',
				'mountText':'Badger',
				'notes':'This is a Badger egg.',
				'adjective':'serious',
				'value':4,
				},
			},
		'food' : {
			'Meat' : {
				'key':'Meat',
				'text':'Meat',
				'notes':'A piece of meat.',
				'textA':'A meat',
				'textThe':'The Meat',
				'target':'Base',
				'canDrop':True,
				},
			},
		'eggs' : {
			'wolf' : {
				'key':'wolf',
				'text':'Wolf',
				'mountText':'Wolf',
				'notes':'This is a Wolf egg.',
				'adjective':'fierce',
				'value':3,
				},
			},
		'dropEggs' : {
				'fox' : {
					'key':'fox',
					'text':'Fox',
					'mountText':'Fox',
					'notes':'This is a Fox egg.',
					'adjective':'sly',
					'value':2,
					},
				},
		'hatchingPotions' : {
				'base' : {
					'key':'base',
					'text':'Base',
					'notes':'Makes Base pet.',
					'value':2,
					},
				},
		'wackyHatchingPotions' : {
				'wacky' : {
					'key':'wacky',
					'text':'Wacky',
					'notes':'Makes Wacky pet.',
					'value':3,
					'_addlNotes':'Wacky!',
					'premium':True,
					'limited':True,
					'wacky':True,
					'event':{
						'start':'2020-01-01',
						'end':'2020-01-31',
						},
					},
				},
		'dropHatchingPotions' : {
				'red' : {
					'key':'red',
					'text':'Red',
					'notes':'Makes Red pet.',
					'value':4,
					'premium':False,
					'limited':True,
					'wacky':False,
					},
				},
		'premiumHatchingPotions' : {
				'shadow' : {
					'key':'shadow',
					'text':'Shadow',
					'notes':'Makes Shadow pet.',
					'value':5,
					'_addlNotes':'Premium!',
					'premium':True,
					'limited':False,
					},
				},
		'quests' : {
				'collectionquest' : {
					'key' : 'collectionquest',
					'text' : 'Collect N items',
					'notes' : 'Additional notes',
					'category' : 'pet',
					'goldValue' : 10,
					'group' : 'questgroup1',
					'previous' : 'bossquest',
					'completion' : 'You collected N items!',
					'drop' : {
						'exp' : 500,
						'gp' : 100,
						'items' : [
							{
								'key' : 'fox',
								'text' : 'Fox Egg',
								'type' : 'dropEggs',
								},
							],
						},
					'collect' : {
						'fun' : {
							'key' : 'fun',
							'text' : 'Fun',
							'count' : 10,
							},
						'games' : {
							'key' : 'games',
							'text' : 'Games',
							'count' : 20,
							},
						},
					},
				'bossquest' : {
					'key' : 'bossquest',
					'text' : 'Defeat the Boss',
					'notes' : 'Additional notes',
					'category' : 'unlockable',
					'lvl' : 33,
					'unlockCondition' : {
						'text' : 'Swipe to unlock',
						'condition' : 'login',
						'incentiveThreshold' : 3,
						},
					'group' : 'questgroup1',
					'completion' : 'You defeated the Boss!',
					'drop' : {
						'exp' : 300,
						'gp' : 10,
						'items' : [
							{
								'key' : 'collectionquest',
								'text' : 'Collect N items',
								'type' : 'quests',
								'onlyOwner' : True,
								},
							],
						},
					'boss' : {
						'name' : 'The Boss',
						'hp' : 500,
						'str' : 1,
						'def' : 0.5,
						},
					},
				'worldquest' : {
						'key' : 'worldquest',
						'text' : 'Protect the World',
						'notes' : 'Additional notes',
						'category' : 'world',
						'completion' : 'You protected the World!',
						'completionChat' : 'You protected the World!',
						'colors' : {
							'main' : '#ffffff',
							},
						'event':{
							'start':'2020-01-01',
							'end':'2020-01-31',
							},
						'drop' : {
							'exp' : 0,
							'gp' : 0,
							'items' : [
								{
									'key' : 'fox',
									'text' : 'Fox pet',
									'type' : 'questPets',
									},
								],
							},
						'boss' : {
							'name' : 'The World Boss',
							'hp' : 50000,
							'str' : 5,
							'def' : 1.5,
							'rage' : {
								'value' : 500,
								'title' : 'Boss Rage',
								'healing' : 100,
								'description': 'When rage is filled, boss rages!',
								'effect' : 'Boss rages!',
								'stables' : 'Boss rages!',
								'bailey' : 'Boss rages!',
								'guide' : 'Boss rages!',
								'tavern' : 'Boss rages!',
								'quests' : 'Boss rages!',
								},
							},
						},
				},
				'petInfo': {
						'fox' : {
							'key' : 'fox',
							'text' : 'Fox',
							'type' : 'Base',
							'egg' : 'fox',
							'potion' : 'base',
							'canFind' : True,
							},
						'badger' : {
							'key' : 'badger',
							'text' : 'Badger',
							'type' : 'Clockwork',
							'egg' : 'badger',
							},
						},
				'questPets': {
						'fox':True,
						},
				'specialPets': {
						'fox':False,
						'badger':True,
						},
				'premiumPets': {
						'fox':True,
						},
				'mountInfo': {
						'wolf' : {
							'text' : 'Wolf',
							},
						},
				'mountInfo': {
						'fox' : {
							'key' : 'fox',
							'text' : 'Fox',
							'type' : 'Base',
							'egg' : 'fox',
							'potion' : 'base',
							'canFind' : True,
							},
						'wolf' : {
							'key' : 'wolf',
							'text' : 'Wolf',
							'type' : 'Clockwork',
							'egg' : 'wolf',
							},
						},
				'mounts': {
						'fox':True,
						},
				'questMounts': {
						'fox':True,
						},
				'specialMounts': {
						'fox':False,
						'wolf':True,
						},
				'premiumMounts': {
						'fox':True,
						},
				'backgroundFlats': {
						'blizzard' : {
							'key' : 'blizzard',
							'text' : 'Blizzard',
							'notes' : 'Hurling Blizzard',
							'price' : 7,
							'set' : 'Winter',
							},
						},
				'backgrounds': {
						'backgrounds122020' : [
							{
								'key' : 'blizzard',
								'text' : 'Blizzard',
								'notes' : 'Hurling Blizzard',
								'price' : 7,
								'set' : 'Winter',
								},
							],
						'backgrounds082020' : [
							{
								'key' : 'fall',
								'text' : 'Fall',
								'notes' : "Summer's End",
								'price' : 7,
								'set' : 'Fall',
								},
							],
						'timeTravelBackgrounds' : [
							{
								'key' : 'core',
								'text' : 'The Core',
								'notes' : "The Core",
								'price' : 1,
								'currency' : 'hourglass',
								'set' : 'timeTravel',
								},
							],
						},
				"special": {
						"congrats": {
							"key": "congrats",
							"text": "Congratulations Card",
							"mana": 0,
							"target": "user",
							"notes": "Send a Congratulations card to a party member.",
							"value": 10,
							"silent": True,
							"immediateUse": True
							},
						"petalFreePotion": {
							"purchaseType": "debuffPotion",
							"key": "petalFreePotion",
							"text": "Petal-Free Potion",
							"mana": 0,
							"target": "self",
							"notes": "Reverse the spell that made you a flower.",
							"value": 5,
							"immediateUse": True
							},
						"shinySeed": {
							"key": "shinySeed",
							"text": "Shiny Seed",
							"mana": 0,
							"target": "user",
							"previousPurchase": True,
							"value": 15,
							"notes": "Turn a friend into a joyous flower!"
							}
						},
				"cardTypes": {
						"congrats": {
							"key": "congrats",
							"yearRound": True,
							"messageOptions": 5
							},
						},
				"spells": {
						"rogue": {
							"backStab": {
								"key": "backStab",
								"lvl": 12,
								"mana": 15,
								"target": "task",
								"notes": "Betray a task",
								"text": "Backstab"
								},
							"stealth": {
								"key": "stealth",
								"lvl": 14,
								"mana": 45,
								"target": "self",
								"notes": "Be a Ninja",
								"text": "Stealth"
								},
							},
						},
				'userCanOwnQuestCategories' : [
						'unlockable',
						'pet',
						],
				'gear' : {
						'flat' : {
							'ninja_katana' : {
								"text": "Katana",
								"notes": "Ninja Katana.",
								"key": "ninja_katana",
								"klass": "rogue",
								"set": "ninja-1",
								"int": 1,
								"index": "1",
								"type": "weapon",
								"per": 3,
								"value": 100,
								"con": 0,
								"str": 5,
								},
							'daikatana' : {
								"text": "Daiatana",
								"notes": "Daikatana!",
								"key": "daikatana",
								"klass": "special",
								"specialClass": "rogue",
								"set": "ninja-special",
								"int": 1,
								"index": "special",
								"type": "weapon",
								"per": 3,
								"value": 100,
								"con": 0,
								"str": 5,
								'event':{
									'start':'2020-01-01',
									'end':'2020-01-31',
									},
								"last": True,
								'gearSet' : 'DOOM',
								},
							'mysterykatana' : {
								"text": "Mystery Katana",
								"notes": "Mystery Katana!",
								"key": "mysterykatana",
								"klass": "mystery",
								"mystery": "202012",
								"twoHanded": True,
								},
							},
						'tree' : {
							'weapon' : {
								'rogue' : {
									'katana' : {
										"text": "Katana",
										"key": "ninja_katana",
										},
									},
								},
							},
						},
						'mystery' : {
								'202012' : {
									'items' : [
										{
											'key' : 'ninja_katana',
											},
										],
									"text": "Mystery Ninja",
									"class": "set_mystery_202012",
									"start": "2020-12-01",
									"end": "2020-12-31",
									"key": "202012",
									},
								},
						}
