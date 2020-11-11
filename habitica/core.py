#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Phil Adams http://philadams.net

habitica: commandline interface for http://habitica.com
http://github.com/philadams/habitica

TODO:philadams add logging to .api
TODO:philadams get logger named, like requests!
"""


from bisect import bisect
import json
import logging
import netrc
import os.path
import datetime
import sys
import time
import html
import re
import argparse
import functools, itertools
from time import sleep
from webbrowser import open_new_tab


try:
    from . import api
    from . import timeutils, config
    from . import extra
except SystemError:
    pass # to allow import for doctest
except ValueError:
    pass # to allow import for doctest

from pprint import pprint

def dump_json(obj, filename):
    with open(filename, 'wb') as f:
        f.write(json.dumps(obj, indent=4, ensure_ascii=False).encode('utf-8'))

def load_json(filename):
    with open(filename, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))


VERSION = 'habitica version 0.0.12'
TASK_VALUE_BASE = 0.9747  # http://habitica.wikia.com/wiki/Task_Value
HABITICA_REQUEST_WAIT_TIME = 0.5  # time to pause between concurrent requests
HABITICA_TASKS_PAGE = '/#/tasks'
# https://trello.com/c/4C8w1z5h/17-task-difficulty-settings-v2-priority-multiplier
PRIORITY = {'easy': 1,
            'medium': 1.5,
            'hard': 2}

def task_id_key(task_id):
    SUBTASK_ORDER, TASK_ORDER = 0, 1
    if isinstance(task_id, int):
        return (task_id, TASK_ORDER, 0)
    else:
        task_id, subtask_id = task_id
        return (task_id, SUBTASK_ORDER, subtask_id)

def parse_task_number_arg(raw_arg):
    task_ids = []
    for bit in raw_arg.split(','):
        if '-' in bit:
            start, stop = [int(e) - 1 for e in bit.split('-')]
            task_ids.extend(range(start, stop + 1))
        elif '.' in bit:
            task_ids.append(tuple([int(e) - 1 for e in bit.split('.')]))
        else:
            task_ids.append(int(bit) - 1)
    return task_ids

def find_task_in_list(raw_arg, task_list):
    matching_tasks = []
    for index, task in enumerate(task_list):
        if raw_arg in task['text']:
            matching_tasks.append(index)
        if 'checklist' in task:
            for subindex, subitem in enumerate(task['checklist']):
                if raw_arg in subitem['text']:
                    matching_tasks.append( (index, subindex) )
    if not matching_tasks:
        print("couldn't find task that includes '{0}'".format(raw_arg))
        return None
    if len(matching_tasks) > 1:
        print("task arg '{0}' is ambiguous:".format(raw_arg))
        for tid in matching_tasks:
            if isinstance(tid, tuple):
                tid, item_id = tid
                print("  '{0} : {1}'".format(task_list[tid]['text'], task_list[tid]['checklist'][item_id]['text']))
            else:
                print("  '{0}'".format(task_list[tid]['text']))
        return None
    return matching_tasks[0]

def get_task_ids(tids, task_list=None):
    """
    handle task-id formats such as:
        habitica todos done 3
        habitica todos done 1,2,3
        habitica todos done 2 3
        habitica todos done 1-3,4 8
    tids is a seq like (last example above) ('1-3,4' '8')
    subitems could be specified using format '1.1 1.2'
    titles could be used (full or partial, but ambiguity will trigger an exception)
    """
    logging.debug('raw task ids: %s' % tids)
    task_ids = []
    TASK_NUMBERS = re.compile(r'^(\d+(-\d+)?,?)+')
    for raw_arg in tids:
        if TASK_NUMBERS.match(raw_arg):
            task_ids.extend(parse_task_number_arg(raw_arg))
        elif task_list is not None:
            task_id = find_task_in_list(raw_arg, task_list)
            if task_id is not None:
                task_ids.append(task_id)
        else:
            print("cannot parse task id arg: '{0}'".format(raw_arg))
    return sorted(task_ids, key=task_id_key)


def updated_task_list(tasks, tids):
    for tid in sorted(tids, key=task_id_key, reverse=True):
        if isinstance(tid, tuple):
            continue
        del(tasks[tid])
    return tasks

def print_task_list(tasks, hide_completed=False, timezoneOffset=0, with_notes=False):
    for i, task in enumerate(tasks):
        if 'type' in task and task['type'] == 'daily':
            if task['frequency'] == 'daily':
                if timeutils.days_passed(task['startDate'], datetime.datetime.now(), timezoneOffset=timezoneOffset) % task['everyX'] != 0:
                    continue
            elif task['frequency'] == 'weekly':
                habitica_week = ["m", "t", "w", "th", "f", "s", "su"]
                if not task['repeat'][habitica_week[datetime.datetime.now().weekday()]]:
                    continue
            else:
                print("Unknown daily frequency: {0}".format(task['frequency']))
        if 'completed' in task:
            completed = 'x' if task['completed'] else ' '
            if task['completed'] and hide_completed:
                continue
            print('[%s] %s %s' % (completed, i + 1, task['text']))
        else:
            print('%s %s' % (i + 1, task['text']))
        if with_notes:
            print('\n'.join('      {0}'.format(line) for line in task['notes'].splitlines()))
        if 'checklist' in task:
            for j, item in enumerate(task['checklist']):
                completed = 'x' if item['completed'] else ' '
                print('    [%s] %s.%s %s' % (completed, i + 1, j + 1, item['text']))

def qualitative_task_score_from_value(value):
    # task value/score info: http://habitica.wikia.com/wiki/Task_Value
    scores = ['<<<   ', ' <<   ', '  <   ', '      ', '   >  ', '   >> ', '   >>>']
    breakpoints = [-20, -10, -1, 1, 5, 10]
    return scores[bisect(breakpoints, value)]

@functools.lru_cache()
def get_target_list(hbt, target_type):
    if target_type == 'habit':
        return hbt.tasks.user(type='habits')
    else:
        raise ValueError('Unknown spell target type: {0}'.format(target_type))

def get_target_uuid(hbt, target_type, target_pattern):
    targets = get_target_list(hbt, target_type)
    ids = get_task_ids([target_pattern], task_list=targets)
    return [targets[i]['_id'] for i in ids]

def cli():
    parser = argparse.ArgumentParser(description='Habitica command-line interface.')
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--difficulty', choices=['easy', 'medium', 'hard'],
            default='easy')
    parser.add_argument('--verbose', action='store_true', default=False,
            help='Show some logging information')
    parser.add_argument('--debug', action='store_true', default=False,
            help='Show all logging information')
    parser.add_argument('--full', action='store_true', default=False,
            help='Print tasks details along with the title.')
    parser.add_argument('--list-all', action='store_true', default=False,
            help='List all dailies. By default only not done dailies will be displayed')

    commands = parser.add_subparsers(dest='command', help='Habitica commands')
    commands.add_parser('status', help='Show HP, XP, GP, and more')
    command_habits = commands.add_parser('habits', help='Manage habit tasks')
    command_habits.add_argument('action', nargs='?', choices=['up', 'down', 'list'], default='list', help='Habits action: List habit tasks, Up (+) habit, Down (-) habit')
    command_habits.add_argument('task', nargs='*', default=[],
            help='You can pass one or more <task-id> parameters, using either comma-separated lists or ranges or both. For example, `todos done 1,3,6-9,11`.')
    command_dailies = commands.add_parser('dailies', help='Manage daily tasks')
    command_dailies.add_argument('action', nargs='?', choices=['done', 'undo', 'list'], default='list', help='Habits action: List daily tasks, Mark daily complete, Mark daily incomplete')
    command_dailies.add_argument('task', nargs='*', default=[],
            help='You can pass one or more <task-id> parameters, using either comma-separated lists or ranges or both. For example, `todos done 1,3,6-9,11`.')
    command_todos = commands.add_parser('todos', help='Manage todo tasks')
    command_todos.add_argument('action', nargs='?', choices=['done', 'add', 'list'], default='list', help='Habits action: List todo tasks, Mark one or more todo completed, Add todo with description')
    command_todos.add_argument('task', nargs='*', default=[],
            help='You can pass one or more <task-id> parameters, using either comma-separated lists or ranges or both. For example, `todos done 1,3,6-9,11`. For action "add" it must be a new task title instead.')
    commands.add_parser('health', help='Buy health potion')
    command_spells = commands.add_parser('spells', help='Casts or list available spells')
    command_spells.add_argument('cast', nargs='?', help='Spell to cast. By default lists available spells.')
    command_spells.add_argument('--habit', action='store_const', dest='target_type', const='habit', help='Indicates that targets are habits.')
    command_spells.add_argument('targets', nargs='*', default=[], help='Targets to cast spell on.')
    command_messages = commands.add_parser('messages', help='Lists last messages for all guilds user is in.')
    command_messages.add_argument('count', nargs='?', type=int, default=0, help='Max count of messages displayed, if 0 (default) displays all.')
    command_messages.add_argument('--seen', action='store_true', default=False, help='Mark all messages as read.')
    command_messages.add_argument('--json', action='store_true', default=False, help='Print all messages in JSON format.')
    command_messages.add_argument('--rss', action='store_true', default=False, help='Print all messages in RSS format.')
    commands.add_parser('server', help='Show status of Habitica service')
    commands.add_parser('home', help='Open tasks page in default browser')

    command_reward = commands.add_parser('reward', help='Buys or lists available items in reward column')
    command_reward.add_argument('item', nargs='?', help='Item to buy. By default lists available items.')

    # set up args
    args = parser.parse_args()

    # set up logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug('Command line args: {%s}' %
                  ', '.join("'%s': '%s'" % (k, v) for k, v in vars(args).items()))

    # Set up auth
    auth = config.load_auth()

    # Prepare cache
    cache = config.Cache()

    # instantiate api service
    hbt = api.Habitica(auth=auth)

    # GET server status
    if args.command == 'server':
        server = hbt.status()
        if server['status'] == 'up':
            print('Habitica server is up')
        else:
            print('Habitica server down... or your computer cannot connect')

    # open HABITICA_TASKS_PAGE
    elif args.command == 'home':
        home_url = '%s%s' % (auth['url'], HABITICA_TASKS_PAGE)
        print('Opening %s' % home_url)
        open_new_tab(home_url)

    # messages
    elif args.command == 'messages':
        mark_as_seen = args.seen
        as_json = args.json
        as_rss = args.rss
        if as_json and as_rss:
            print('Only one type of export could be specified: --rss, --json')
            sys.exit(1)
        max_count = 0 # By default no restriction - print all messages.
        if args.count:
            max_count = int(args.count)

        groups = hbt.groups(type='guilds')
        if not groups:
            print('Failed to fetch list of user guilds', file=sys.stderr)
            return
        groups.extend(hbt.groups(type='party'))
        if as_rss:
            exporter = extra.RSSMessageFeed()
        elif as_json:
            exporter = extra.JsonMessageFeed()
        else:
            exporter = extra.TextMessageFeed()
        for group in groups:
            group_name = group['name']
            chat_messages = hbt.groups[group['id']].chat()
            if not chat_messages:
                logging.error('Failed to fetch messages of chat {0}'.format(group_name))
                continue
            if max_count:
                chat_messages = chat_messages[:max_count]
            for entry in chat_messages:
                message = {
                        'id' : entry['id'],
                        'username': entry['user'] if 'user' in entry else 'system',
                        'timestamp': int(int(entry['timestamp']) / 1000),
                        'text': entry['text'],
                        }
                exporter.add_message(group, message)
            if mark_as_seen:
                hbt.groups[group['id']]['chat'].seen(_method='post')
        exporter.done()

    # GET user
    elif args.command == 'status':

        # gather status info
        user = hbt.user()
        party = hbt.groups.party()
        stats = user.get('stats', '')
        items = user.get('items', '')
        food_count = sum(items['food'].values())

        # gather quest progress information (yes, janky. the API
        # doesn't make this stat particularly easy to grab...).
        # because hitting /content downloads a crapload of stuff, we
        # cache info about the current quest in cache.
        quest = 'Not currently on a quest'
        if (party is not None and
                party.get('quest', '') and
                party.get('quest').get('active')):

            quest_key = party['quest']['key']

            if cache.get(cache.SECTION_CACHE_QUEST, 'quest_key') != quest_key:
                # we're on a new quest, update quest key
                logging.info('Updating quest information...')
                content = hbt.content()
                quest_type = ''
                quest_max = '-1'
                quest_title = content['quests'][quest_key]['text']

                # if there's a content/quests/<quest_key/collect,
                # then drill into .../collect/<whatever>/count and
                # .../collect/<whatever>/text and get those values
                if content.get('quests', {}).get(quest_key, {}).get('collect'):
                    logging.debug("\tOn a collection type of quest")
                    quest_type = 'collect'
                    clct = list(content['quests'][quest_key]['collect'].values())[0]
                    quest_max = clct['count']
                # else if it's a boss, then hit up
                # content/quests/<quest_key>/boss/hp
                elif content.get('quests', {}).get(quest_key, {}).get('boss'):
                    logging.debug("\tOn a boss/hp type of quest")
                    quest_type = 'hp'
                    quest_max = content['quests'][quest_key]['boss']['hp']

                # store repr of quest info from /content
                cache.update_quest_cache(
                        quest_key=str(quest_key),
                        quest_type=str(quest_type),
                        quest_max=str(quest_max),
                        quest_title=str(quest_title),
                        )

            # now we use /party and quest_type to figure out our progress!
            quest_type = cache.get(cache.SECTION_CACHE_QUEST, 'quest_type')
            if quest_type == 'collect':
                qp_tmp = party['quest']['progress']['collect']
                try:
                    quest_progress = list(qp_tmp.values())[0]['count']
                except TypeError:
                    quest_progress = list(qp_tmp.values())[0]
            else:
                quest_progress = party['quest']['progress']['hp']

            quest = '%s/%s "%s"' % (
                    str(int(quest_progress)),
                    cache.get(cache.SECTION_CACHE_QUEST, 'quest_max'),
                    cache.get(cache.SECTION_CACHE_QUEST, 'quest_title'))

        # prepare and print status strings
        title = 'Level %d %s' % (stats['lvl'], stats['class'].capitalize())
        health = '%d/%d' % (stats['hp'], stats['maxHealth'])
        xp = '%d/%d' % (int(stats['exp']), stats['toNextLevel'])
        mana = '%d/%d' % (int(stats['mp']), stats['maxMP'])
        gold = '%d' % (int(stats['gp']),)
        currentPet = items.get('currentPet', '')
        pet = '%s (%d food items)' % (currentPet, food_count)
        mount = items.get('currentMount', '')
        summary_items = ('health', 'xp', 'mana', 'gold', 'quest', 'pet', 'mount')
        len_ljust = max(map(len, summary_items)) + 1
        print('-' * len(title))
        print(title)
        print('-' * len(title))
        print('%s %s' % ('Health:'.rjust(len_ljust, ' '), health))
        print('%s %s' % ('XP:'.rjust(len_ljust, ' '), xp))
        print('%s %s' % ('Mana:'.rjust(len_ljust, ' '), mana))
        print('%s %s' % ('Gold:'.rjust(len_ljust, ' '), gold))
        print('%s %s' % ('Pet:'.rjust(len_ljust, ' '), pet))
        print('%s %s' % ('Mount:'.rjust(len_ljust, ' '), mount))
        print('%s %s' % ('Quest:'.rjust(len_ljust, ' '), quest))

    # POST buy health potion
    elif args.command == 'health':
        HEALTH_POTION_VALUE = 15.0
        user = hbt.user()
        stats = user.get('stats', '')
        if stats['hp'] + HEALTH_POTION_VALUE > stats['maxHealth']:
            print('HP is too high, part of health potion would be wasted.')
            print('HP: {0:.1f}/{1}, need at most {2:.1f}'.format(stats['hp'], stats['maxHealth'], stats['maxHealth'] - HEALTH_POTION_VALUE))
        else:
            new_stats = hbt.user['buy-health-potion'](_method='post')
            print('Bought Health Potion, HP: {0:.1f}/{1}'.format(new_stats['hp'], stats['maxHealth']))

    # list/POST buy reward column's item
    elif args.command == 'reward':
        rewards = hbt.tasks.user(type='rewards')
        if args.item is None:
            print_task_list(rewards)
        else:
            tids = get_task_ids([args.item], task_list=rewards)
            for tid in tids:
                hbt.tasks[rewards[tid]['id']].score(
                               _direction='up', _method='post')
                print('bought reward \'%s\''
                      % rewards[tid]['text'])

    # list/POST spells
    elif args.command == 'spells':
        SPELLS = {
                'mage' : {
                    'fireball': "Burst of Flames",
                    'mpHeal': "Ethereal Surge",
                    'earth': "Earthquake",
                    'frost': "Chilling Frost",
                    },

                'warrior' : {
                    'smash': "Brutal Smash",
                    'defensiveStance': "Defensive Stance",
                    'valorousPresence': "Valorous Presence",
                    'intimidate': "Intimidating Gaze",
                    },

                'rogue' : {
                    'pickPocket': "Pickpocket",
                    'backStab': "Backstab",
                    'toolsOfTrade': "Tools of the Trade",
                    'stealth': "Stealth",
                    },

                'healer' : {
                    'heal': "Healing Light",
                    'protectAura': "Protective Aura",
                    'brightness': "Searing Brightness",
                    'healAll': "Blessing",
                    },
                }
        user = hbt.user()
        user_class = user['stats']['class']
        if args.cast:
            spell_name, targets = args.cast, args.targets
            if spell_name not in SPELLS[user_class]:
                print('{1} cannot cast spell {0}'.format(user_class.title(), spell_name))
            else:
                if args.targets and not args.target_type:
                    print('Target type is not specified!')
                    sys.exit(1)
                if args.targets:
                    target_uuids = itertools.chain.from_iterable(get_target_uuid(hbt, args.target_type, target) for target in args.targets)
                    for target_uuid in target_uuids:
                        params = {'targetId' : target_uuid}
                        result = hbt.user['class']['cast'][spell_name](_params=params, _method='post')
                        if result is not None:
                            print('Casted spell "{0}"'.format(SPELLS[user_class][spell_name]))
                        else:
                            sys.exit(1)
                else:
                    hbt.user['class']['cast'][spell_name](_method='post')
                    print('Casted spell "{0}"'.format(SPELLS[user_class][spell_name]))
        else:
            for name, description in SPELLS[user_class].items():
                print('{0} - {1}'.format(name, description))

    # GET/POST habits
    elif args.command == 'habits':
        habits = hbt.tasks.user(type='habits')
        if 'up' == args.action:
            tids = get_task_ids(args.task, task_list=habits)
            for tid in tids:
                if not habits[tid]['up']:
                    print("task '{0}' cannot be incremented".format(habits[tid]['text']))
                    continue
                tval = habits[tid]['value']
                hbt.tasks[habits[tid]['id']].score(
                               _direction='up', _method='post')
                print('incremented task \'%s\''
                      % habits[tid]['text'])
                habits[tid]['value'] = tval + (TASK_VALUE_BASE ** tval)
                sleep(HABITICA_REQUEST_WAIT_TIME)
        elif 'down' == args.action:
            tids = get_task_ids(args.task, task_list=habits)
            for tid in tids:
                if not habits[tid]['down']:
                    print("task '{0}' cannot be decremented".format(habits[tid]['text']))
                    continue
                tval = habits[tid]['value']
                hbt.tasks[habits[tid]['id']].score(
                               _direction='down', _method='post')
                print('decremented task \'%s\''
                      % habits[tid]['text'])
                habits[tid]['value'] = tval - (TASK_VALUE_BASE ** tval)
                sleep(HABITICA_REQUEST_WAIT_TIME)
        with_notes = args.full
        for i, task in enumerate(habits):
            score = qualitative_task_score_from_value(task['value'])
            updown = {0:' ', 1:'-', 2:'+', 3:'±'}[int(task['up'])*2 + int(task['down'])] # [up][down] as binary number
            print('[{3}|{0}] {1} {2}'.format(score, i + 1, task['text'], updown))
            if with_notes:
                print('\n'.join('      {0}'.format(line) for line in task['notes'].splitlines()))

    # GET/PUT tasks:daily
    elif args.command == 'dailies':
        user = hbt.user()
        if not user:
            print('Failed to load user dailies', file=sys.stderr)
            return
        timezoneOffset = user['preferences']['timezoneOffset']
        dailies = hbt.tasks.user(type='dailys')
        if 'done' == args.action:
            tids = get_task_ids(args.task, task_list=dailies)
            for tid in tids:
                item_id = None
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    if not dailies[tid]['checklist'][item_id]['completed']:
                        hbt.tasks[dailies[tid]['id']]['checklist'][dailies[tid]['checklist'][item_id]['id']].score(
                                       _method='post')
                        print("marked daily '{0} : {1}' complete".format(dailies[tid]['text'], dailies[tid]['checklist'][item_id]['text']))
                        dailies[tid]['checklist'][item_id]['completed'] = True
                else:
                    hbt.tasks[dailies[tid]['id']].score(
                                   _direction='up', _method='post')
                    print('marked daily \'%s\' completed'
                          % dailies[tid]['text'])
                    dailies[tid]['completed'] = True
                sleep(HABITICA_REQUEST_WAIT_TIME)
        elif 'undo' == args.action:
            tids = get_task_ids(args.task, task_list=dailies)
            for tid in tids:
                item_id = None
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    if dailies[tid]['checklist'][item_id]['completed']:
                        hbt.tasks[dailies[tid]['id']]['checklist'][dailies[tid]['checklist'][item_id]['id']].score(
                                       _method='post')
                        print("marked daily '{0} : {1}' incomplete".format(dailies[tid]['text'], dailies[tid]['checklist'][item_id]['text']))
                        dailies[tid]['checklist'][item_id]['completed'] = False
                else:
                    hbt.tasks[dailies[tid]['id']].score(
                                   _direction='down', _method='post')
                    print('marked daily \'%s\' incomplete'
                          % dailies[tid]['text'])
                    dailies[tid]['completed'] = False
                sleep(HABITICA_REQUEST_WAIT_TIME)
        print_task_list(dailies, hide_completed=not args.list_all, timezoneOffset=timezoneOffset, with_notes=args.full)

    # GET tasks:todo
    elif args.command == 'todos':
        todos = [e for e in hbt.tasks.user(type='todos')
                 if not e['completed']]
        if 'done' == args.action:
            tids = get_task_ids(args.task, task_list=todos)
            for tid in tids:
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    if not todos[tid]['checklist'][item_id]['completed']:
                        hbt.tasks[todos[tid]['id']]['checklist'][todos[tid]['checklist'][item_id]['id']].score(
                                       _method='post')
                        print("marked todo '{0} : {1}' complete".format(todos[tid]['text'], todos[tid]['checklist'][item_id]['text']))
                        todos[tid]['checklist'][item_id]['completed'] = True
                else:
                    hbt.tasks[todos[tid]['id']].score(
                                   _direction='up', _method='post')
                    print('marked todo \'%s\' complete'
                          % todos[tid]['text'])
                sleep(HABITICA_REQUEST_WAIT_TIME)
            todos = updated_task_list(todos, tids)
        elif 'add' == args.action:
            ttext = ' '.join(args.task)
            hbt.tasks(type='todos',
                           text=ttext,
                           priority=PRIORITY[args.difficulty],
                           _method='post')
            todos.insert(0, {'completed': False, 'text': ttext})
            print('added new todo \'%s\'' % ttext)
        with_notes = args.full
        print_task_list(todos, with_notes=args.full)


if __name__ == '__main__':
    cli()
