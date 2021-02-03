import types, copy
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
		super().__init__(method, path, {'data':copy.deepcopy(data)}, cached=cached)

class MockAPI:
	""" /content call is cached. """
	def __init__(self, *requests):
		self.base_url = 'http://localhost'
		self.requests = list(requests)
		self.responses = []
		self.cache = [
			MockRequest('get', ['content'], {'data': MockData.CONTENT_DATA}, cached=True),
			]
		self.hook = None
	def set_response_hook(self, hook):
		self.hook = hook
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
		if self.hook:
			self.hook(request.response)
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

class OrderedDataAccess:
	def __init__(self, parent):
		self.parent = parent
	def __getattr__(self, attr):
		obj = getattr(self.parent, attr)
		return [value for key, value in sorted(obj.items(), key=lambda _:_[0])]

MockData.ORDERED = OrderedDataAccess(MockData)

MockData.USER = {
		'id' : 'jcdenton',
		'profile' : {
			'name' : 'JC Denton',
			'blurb' : 'not-explained',
			'imageUrl' : 'jcdenton-image',
			},
		'balance' : 10,
		'loginIncentives' : 400,
		'invitesSent' : 2,
		'needsCron' : False,
		'lastCron' : '2016-06-20T21:00:00.000Z',
		'flags' : {
			'not' : 'explained',
			},
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
			'buffs' : {
				'str' : 1,
				'int' : 2,
				'per' : 1,
				'con' : 0,
				'stealth' : True,
				'streaks' : True,
				'snowball' : False,
				'spookySparkles' : False,
				'shinySeeds' : False,
				'seafoam' : False,
				},
			'training' : {
				'str' : 0,
				'int' : 1,
				'per' : 1,
				'con' : 2,
				},
			},
		'party' : {
			'quest' : {
				'key' : 'laguardia1',
				'progress' : {
					'up' : 'not-explained',
					'down' : 'not-explained',
					'collect' : 'not-explained',
					'collectedItems' : 'not-explained',
					},
				'completed' : 'not-explained',
				'RSVPNeeded' : False,
				},
			},
		'preferences' : {
			'timezoneOffset' : 180,
			'timezoneOffsetAtLastCron' : 180,
			'dayStart' : 180,
			'hideHeader' : True,
			'language' : 'en',
			'automaticAllocation' : False,
			'allocationMode' : 'not-explained',
			'autoEquip' : False,
			'costume' : True,
			'dateFormat' : 'not-explained',
			'sleep' : False,
			'stickyHeader' : False,
			'disableClasses' : False,
			'newTaskEdit' : False,
			'dailyDueDefaultView' : False,
			'advancedCollapsed' : False,
			'toolbarCollapsed' : False,
			'reverseChatOrder' : False,
			'background' : False,
			'displayInviteToPartyWhenPartyIs1' : False,
			'improvementCategories' : False,
			'size' : 1,
			'hair' : {
				'color' : 2,
				'base' : 3,
				'bangs' : 4,
				'beard' : 5,
				'mustache' : 6,
				'flower' : 7,
				},
			'skin' : 8,
			'shirt' : 9,
			'sound' : 10,
			'chair' : 11,
			},
		'items' : {
			'lastDrop' : {
				'date' : 'not-explained',
				'count' : 'not-explained',
				},
			'eggs' : { 'not' : 'explained', },
			'hatchingPotions' : { 'not' : 'explained', },
			'quests' : { 'not' : 'explained', },
			'pets' : { 'not' : 'explained', },
			'mounts' : { 'not' : 'explained', },
			'gear' :{
				'owned' : { 'not' : 'explained', },
				'costume' : {
					'weapon' : 'ninja_katana',
					'armor' : 'Dummy',
					'head' : 'Dummy',
					'shield' : 'Dummy',
					'back' : 'Dummy',
					'headAccessory' : 'Dummy',
					'eyewear' : 'Dummy',
					'body' : 'Dummy',
					},
				'equipped' : {
					'weapon' : 'ninja_katana',
					'armor' : 'Dummy',
					'head' : 'Dummy',
					'shield' : 'Dummy',
					'back' : 'Dummy',
					'headAccessory' : 'Dummy',
					'eyewear' : 'Dummy',
					'body' : 'Dummy',
					},
				},
			'food' : {
				'Meat' : 2,
				'Honey' : 1,
				},
			'currentPet' : 'fox',
			'currentMount' : 'wolf',
			},
		'purchased' : {
				'plan' : {
					'gemsBought' : 3,
					'consecutive': {
						'gemCapExtra' : 25,
						},
					},
				},
		'notifications' : [
				{
					'id' : 'helios1',
					'text' : 'We have existed in isolation.',
					'seen' : False,
					},
				{
					'id' : 'helios2',
					'text' : 'Pure. Disconnected. Alone. Stagnant.',
					'seen' : False,
					},
				],
		}

MockData.REWARDS = {
		'augments' : {
			'id':'augments',
			'type':'reward',
			'text':'Use augmentation canister',
			'value' : 100,
			},
		'read' : {
			'id':'read',
			'text':'Read "The man who was Thursday"',
			},
		}

MockData.TODOS = {
		'majestic12' : {
			'id':'majestic12',
			'text':'Escape Majestic 12 facilities',
			'notes':'Be stealth as possible',
			'type' : 'todo',
			'createdAt' : 1600000000,
			'updatedAt' : 1600000000,
			'value' : 10,
			'byHabitica' : False,
			'alias' : 'escape',
			'priority' : 'not-explained',
			'attribute' : 'dex',
			'userId' : 'jcdenton',
			'reminders' : ['not-explained'],
			'completed':False,
			'checklist': [
				{
					'id':'armory',
					'text':'Get back all equipment',
					'completed':True,
					},
				{
					'id':'killswitch',
					'text':'Get killswitch schematics from medlab',
					'completed':False,
					},
				],
			},
		'liberty' : {
			'id': 'liberty',
			'type' : 'todo',
			'text': 'Free Liberty statue and resque agent.',
			'alias' : 'liberty statue',
			'date' : '2016-06-20',
			'dateCompleted' : 'not-explained',
			'group' : {
				'id' : 'unatco',
				'broken' : False,
				'assignedUsers' : ['jcdenton'],
				'assignedDate' : 'DATE',
				'assignedUsername' : 'pauldenton',
				'taskId' : 'liberty',
				'sharedCompletion' : False,
				'managerNotes' : 'Track progress of agent.',
				'approval' : {
					'required' : True,
					'requested' : True,
					'requestedDate' : 'DATE',
					'dateApproved' : 'DATE',
					'approvingUser' : 'manderley',
					},
				},
			'challenge' : {
				'id' : 'unatco',
				'shortName' : 'UNATCO',
				'taskId' : 'liberty',
				'broken' : True,
				'winner' : 'jcdenton',
				},
			},
		}

MockData.DAILIES = {
		'armory' : {
			'id':'armory',
			'type' : 'daily',
			'text':'Restock at armory',
			'notes':'See Sam Carter for equipment',
			'completed':False,
			'collapseChecklist': False,
			'value' : 10,
			'streak' : 3,
			'yesterDaily' : False,
			'frequency' : 'daily',
			'isDue' : True,
			'nextDue' : '2016-06-20T21:00:00.000Z',
			'checklist': [
				{
					'id':'stealthpistol',
					'text':'Ask for stealth pistol',
					'completed':True,
					},
				{
					'id':'lockpick',
					'text':'Choose lockpick',
					'completed':False,
					},
				],
			},
		'manderley' : {
			'id':'manderley',
			'type' : 'daily',
			'text':'Manderley',
			'notes':'Visit Manderley for new missions',
			'frequency':'daily',
			'startDate':'2016-06-20T21:00:00.000Z',
			'everyX':12,
			'daysOfMonth':1,
			'weeksOfMonth':1,
			},
		'medbay' : {
			'id':'medbay',
			'type' : 'daily',
			'text':'Visit medbay on Monday',
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
		}

MockData.HABITS = {
		'bobpage' : {
			'id' : 'bobpage',
			'text' : 'Join Bob Page',
			'value':-50.1,
			'up':True,
			'down':False,
			},
		'shoot' : {
			'id':'shoot',
			'text':'Shoot terrorists',
			'notes':'And gain respect of Anna Navarre',
			'value':-15.4,
			},
		'carryon' : {
			'id':'carryon',
			'text':'Carry on, agent',
			'value':-5.6,
			'up':False,
			'down':False,
			},
		'steal' : {
			'text' : 'Steal credits from ATMs',
			'value':0.0,
			},
		'upgrade' : {
			'text' : 'Upgrade weapons',
			'value':1.1,
			},
		'stealth' : {
			'id' : 'stealth',
			'type' : 'habit',
			'text' : 'Be quiet as possible',
			'value':5.1,
			'up' : True,
			'down':True,
			'counterUp' : 3,
			'counterDown' : 1,
			'frequency' : 'daily',
			},
		'civilian': {
			'text' : 'Keep civilian safe',
			'value':15.1,
			},
		}

MockData.GROUPS = {
	'party' : {
		'id': 'party',
		'name' : 'Denton brothers',
		'type' : 'party',
		'summary' : 'Paul and JC',
		'description' : 'Coalition of Paul and JC Denton',
		'privacy' : 'private',
		'bannedWordsAllowed' : True,
		'leaderOnly' : {
			'challenges' : True,
			'getGems' : False,
			},
		'leader' : 'pauldenton',
		'memberCount' : 1,
		'challengeCount' : 0,
		'balance' : 1,
		'logo' : 'deusex-logo',
		'leaderMessage' : 'Way to go',
		'quest' : {
			'active' : True,
			'key' : 'laguardia1',
			'progress' : {
				'collect' : {
					'ambrosia' : 1,
					'turret' : 5,
					}
				},
			},
		'tasksOrder' : {
			'rewards' : ['augments'],
			'todos' : ['liberty'],
			'dailys' : ['armory'],
			'habits' : ['carryon'],
			},
		},
	'unatco' : {
		'id' : 'unatco',
		'name' : 'UNATCO',
		'type' : 'guild',
		'privacy' : 'public',
		},
	'nsf' : {
		'id' : 'nsf',
		'name' : 'NSF',
		'type' : 'guild',
		'privacy' : 'public',
		'quest' : {
			'active' : True,
			'key' : '747',
			'leader' : 'jcdenton',
			'rage' : 1.05,
			'progress' : {
				'hp' : 20,
				},
			},
		},
	'tavern' : {
		'id' : 'tavern',
		'name' : 'Tavern',
		'type' : 'habitrpg',
		},
	'illuminati' : {
		'name' : 'Illuminati',
		'id' : 'illuminati',
		'type' : 'guild',
		'privacy' : 'private',
		'quest' : {
			'active' : True,
			'key' : 'area51',
			'leader' : 'jcdenton',
			'rage' : 1.05,
			'progress' : {
				'hp' : 20,
				},
			},
		},
	}
MockData.BOSS_QUEST_PROGRESS = {
		'active' : True,
		'key' : '747',
		'progress': {
			'hp' : 20,
			},
		}

MockData.PARTY_CHAT = [
		{
			'id' : 'chat1',
			'user' : 'jcdenton',
			'timestamp' : 1600000000,
			'text' : 'Hello Paul',
			},
		{
			'id' : 'chat2',
			'user' : 'pauldenton',
			'timestamp' : 1600001000,
			'text' : 'Hello JC',
			}
		]
MockData.PARTY_CHAT_FLAGGED = {
		'id' : 'chat3',
		'user' : 'simons',
		'timestamp' : 1600000000,
		'text' : 'Prepare to die!',
		'flagged' : True,
		}
MockData.PARTY_CHAT_LIKED = {
		'id' : 'chat2',
		'user' : 'pauldenton',
		'timestamp' : 1600001000,
		'text' : 'Hello JC',
		'liked' : 1,
		}
MockData.LONG_CHAT = [
		{
			'id' : 'chat5',
			'user' : 'annanavarre',
			'timestamp' : 1600000000,
			'text' : 'I will have to kill you myself.',
			},
		{
			'id' : 'chat6',
			'user' : 'jsdenton',
			'timestamp' : 1600000400,
			'text' : 'Take your best shot, Flatlander Woman.',
			},
		{
			'id' : 'chat7',
			'user' : 'annanavarre',
			'timestamp' : 1600001000,
			'text' : 'How did you know--?',
			}
		]

MockData.CHALLENGES = {
		'unatco' : {
			'id' : 'unatco',
			'name' : 'UNATCO missions',
			'shortName' : 'UNATCO',
			'summary' : 'Missions for UNATCO',
			'description' : 'Perform missions for UNATCO',
			'createdAt' : 1600000000,
			'updatedAt' : 1600000000,
			'prize' : 4,
			'memberCount' : 2,
			'official' : False,
			'leader' : 'manderley',
			'group' : {
				'id': 'unatco',
				'name': 'UNATCO',
				},
			'tasksOrder' : {
				'rewards' : ['augments'],
				'todos' : ['liberty'],
				'dailys' : ['armory'],
				'habits' : ['carryon'],
				},
			},
		'nsf' : {
			'id' : 'nsf',
			'name' : 'NSF missions',
			'shortName' : 'NSF',
			},
		'illuminati' : {
			'id' : 'illuminati',
			'name' : 'Illuminati missions',
			'shortName' : 'Illuminati',
			'summary' : 'Help Illuminati to bring power back',
			},
		}

MockData.TAGS = {
		'unatco' : {
			'id' : 'unatco',
			'name' : 'UNATCO',
			'challenge' : True,
			'group' : 'unatco',
			},
		'nsf' : {
			'id' : 'nsf',
			'name' : 'NSF',
			'challenge' : False,
			'group' : 'nsf',
			},
		'side' : {
			'id' : 'side',
			'name' : 'Side Quest',
			},
		}

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
MockData.MEMBERS = {
		'manderley' : {
			'_id' : 'manderley',
			},
		'joegreen' : {
			'_id' : 'joegreen',
			'profile' : {
				'name' : 'Joe Green',
				},
			},
		'pauldenton' : {
			'_id' : 'pauldenton',
			'profile' : {
				'name' : 'Paul Denton',
				},
			'party' : {
				'id' : 'party',
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
				MockData.DAILIES['manderley'],
				],
			'achievements' : {
				'basic' : MockData.ACHIEVEMENTS['basic'],
				},
			'auth' : {
				'not' : 'explained',
				},
			},
		}
MockData.MEMBERS.update({
	'mj12trooper{0}'.format(i):{
		'id' : 'mj12trooper{0}'.format(i),
		}
	for i in range(1, 31+1)
	})

MockData.NEWS = {
		'title' : 'Latest news',
		'text' : 'Grey Death strikes again!',
		'credits' : 'Joe Green',
		'author' : 'joegreen',
		'publishDate' : '2016-06-20T21:00:00.000Z',
		'published' : False,
		}
MockData.LATEST_NEWS = {
		"html": """<h1>Latest news</h1>
<p>Grey Death strikes again!</p>
"""}

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
			'Honey' : {
				'key':'Honey',
				'text':'Honey',
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
				'laguardia1' : {
					'key' : 'laguardia1',
					'text' : 'Find 3 more barrels of Ambrosia',
					'notes' : 'Also deactivate 5 turret towers',
					'category' : 'unlockable',
					'goldValue' : 10,
					'group' : 'unatco',
					'unlockCondition' : {
						'text' : 'Swipe to unlock',
						'condition' : 'login',
						'incentiveThreshold' : 3,
						},
					'completion' : 'You have found all 4 Ambrosia containers!',
					'drop' : {
						'exp' : 500,
						'gp' : 100,
						'items' : [
							{
								'key' : '747',
								'text' : 'Kill Anna Navarre',
								'type' : 'quests',
								'onlyOwner' : True,
								},
							],
						},
					'collect' : {
						'ambrosia' : {
							'key' : 'ambrosia',
							'text' : 'Barrel of Ambrosia',
							'count' : 3,
							},
						'turret' : {
							'key' : 'turret',
							'text' : 'Turret',
							'count' : 5,
							},
						},
					},
				'747' : {
					'key' : '747',
					'text' : 'Kill Anna Navarre',
					'notes' : 'Additional notes',
					'lvl' : 33,
					'category' : 'pet',
					'previous' : 'laguardia1',
					'group' : 'nsf',
					'completion' : 'You killed Anna Navarre!',
					'drop' : {
						'exp' : 200,
						'gp' : 10,
						'items' : [
							{
								'key' : 'fox',
								'text' : 'Fox Egg',
								'type' : 'dropEggs',
								},
							],
						},
					'boss' : {
						'name' : 'Anna Navarre',
						'hp' : 500,
						'str' : 1,
						'def' : 0.5,
						},
					},
				'area51' : {
						'key' : 'area51',
						'text' : 'Join Illuminati',
						'notes' : 'Kill Bob Page',
						'category' : 'world',
						'completion' : 'You have joined Illuminati!',
						'completionChat' : 'You have joined Illuminati!',
						'value' : 45,
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
							'name' : 'Bob Page',
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
							'Dummy' : {
								'key' : 'Dummy',
								},
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
							'dragonstooth' : {
								"text": "Dragon's Tooth",
								"notes": "A nano sword",
								"key": "dragonstooth",
								"klass": "special",
								"specialClass": "rogue",
								"set": "ninja-special",
								"int": 1,
								"index": "special",
								"type": "weapon",
								"per": 3,
								"value": 15,
								'currency' : 'gems',
								"con": 0,
								"str": 5,
								'event':{
									'start':'2020-01-01',
									'end':'2020-01-31',
									},
								"last": True,
								'gearSet' : 'Nanoweapons',
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
