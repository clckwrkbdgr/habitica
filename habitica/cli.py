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
import logging
import os.path
import datetime
import sys
import re
import argparse
import functools, itertools
import operator
from time import sleep
from webbrowser import open_new_tab
from collections import namedtuple

from . import api, core
from .core import Habitica, Group
from . import timeutils, config
from . import extra

VERSION = 'habitica version 0.1.0'
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
        if hasattr(task, '_data'): # FIXME temporary
            task = task._data
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
        if hasattr(task, '_data'): # FIXME temporary
            task = task._data
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
    command_spells.add_argument('--todo', action='store_const', dest='target_type', const='todo', help='Indicates that targets are todos.')
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

    habitica = Habitica(auth=config.load_auth())
    auth = habitica.auth # FIXME remove with api.Habitica after proper CLI.
    cache = habitica.cache # FIXME remove with api.Habitica after proper CLI.
    hbt = habitica.hbt # FIXME remove with api.Habitica after proper CLI.

    # GET server status
    if args.command == 'server':
        if habitica.server_is_up():
            print('Habitica server is up')
        else:
            print('Habitica server down... or your computer cannot connect')

    # open HABITICA_TASKS_PAGE
    elif args.command == 'home':
        home_url = habitica.home_url()
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

        groups = habitica.groups(Group.GUILDS, Group.PARTY)
        if not groups:
            print('Failed to fetch list of user guilds', file=sys.stderr)
            return
        if as_rss:
            exporter = extra.RSSMessageFeed()
        elif as_json:
            exporter = extra.JsonMessageFeed()
        else:
            exporter = extra.TextMessageFeed()
        for group in groups:
            chat_messages = group.chat()
            if not chat_messages:
                logging.error('Failed to fetch messages of chat {0}'.format(group.name))
                continue
            if max_count:
                chat_messages = chat_messages[:max_count]
            for entry in chat_messages:
                message = {
                        'id' : entry.id,
                        'username': entry.user,
                        'timestamp': int(entry.timestamp / 1000),
                        'text': entry.text,
                        }
                exporter.add_message(group._data, message) # FIXME: Use Group and ChatMessage objects instead.
            if mark_as_seen:
                group.mark_chat_as_read()
        exporter.done()

    # GET user
    elif args.command == 'status':

        # gather status info
        user = habitica.user()
        stats = user.stats

        quest = user.party().quest
        if quest and quest.active:
            quest_info = '{0}/{1} "{2}"'.format(int(quest.progress),
                    quest.max_progress,
                    quest.title)
        else:
            quest_info = 'Not currently on a quest'

        # prepare and print status strings
        title = 'Level %d %s' % (stats.level, stats.class_name.capitalize())
        print('-' * len(title))
        print(title)
        print('-' * len(title))
        rows = [
                ('Health', '%d/%d' % (stats.hp, stats.maxHealth)),
                ('XP', '%d/%d' % (int(stats.experience), stats.maxExperience)),
                ('Mana', '%d/%d' % (int(stats.mana), stats.maxMana)),
                ('Gold', '%d' % (int(stats.gold),)),
                ('Pet', '%s (%d food items)' % (user.inventory.pet, len(user.inventory.food))),
                ('Mount', user.inventory.mount),
                ('Quest', quest_info),
                ]
        len_ljust = max(map(len, map(operator.itemgetter(0), rows))) + 2
        for row_title, value in rows:
            print('%s: %s' % (row_title.rjust(len_ljust, ' '), value))

    # POST buy health potion
    elif args.command == 'health':
        user = habitica.user()
        try:
            user.buy(core.HealthPotion())
            print('Bought Health Potion, HP: {0:.1f}/{1}'.format(user.stats.hp, user.stats.maxHealth))
        except core.HealthOverflowError as e:
            print(e)
            print('HP: {0:.1f}/{1}, need at most {2:.1f}'.format(user.stats.hp, user.stats.maxHealth, user.stats.maxHealth - core.HealthPotion.VALUE))

    # list/POST buy reward column's item
    elif args.command == 'reward':
        user = habitica.user()
        rewards = user.rewards()
        if args.item is None:
            print_task_list(rewards)
        else:
            tids = get_task_ids([args.item], task_list=rewards)
            for tid in tids:
                user.buy(rewards[tid])
                print('bought reward \'%s\'' % rewards[tid].text)

    # list/POST spells
    elif args.command == 'spells':
        user = habitica.user()
        user_class = user.stats.class_name
        if args.cast:
            spell_name, targets = args.cast, args.targets
            spell = user.get_spell(spell_name)
            if not spell:
                print('{1} cannot cast spell {0}'.format(user_class.title(), spell_name))
            else:
                if args.targets and not args.target_type:
                    print('Target type is not specified!')
                    sys.exit(1)
                if args.targets:
                    if args.target_type == 'habit':
                        tasks = user.habits()
                    elif args.target_type == 'todo':
                        tasks = user.todos()
                    else:
                        raise ValueError('Unknown spell target type: {0}'.format(args.target_type))
                    tids = get_task_ids(args.targets, task_list=tasks)
                    for target in [tasks[tid] for tid in tids]:
                        if user.cast(spell, target):
                            print('Casted spell "{0}"'.format(spell.name))
                        else:
                            sys.exit(1)
                else:
                    user.cast(spell)
                    print('Casted spell "{0}"'.format(spell.name))
        else:
            for spell in user.spells():
                print('{0} - {1}'.format(spell.name, spell.description))

    # GET/POST habits
    elif args.command == 'habits':
        habits = habitica.user.habits()
        if 'up' == args.action:
            tids = get_task_ids(args.task, task_list=habits)
            for tid in tids:
                try:
                    habits[tid].up()
                    print('incremented task \'%s\'' % habits[tid].text)
                except CannotScoreUp as e:
                    print(e)
                    continue
        elif 'down' == args.action:
            tids = get_task_ids(args.task, task_list=habits)
            for tid in tids:
                try:
                    habits[tid].down()
                    print('decremented task \'%s\'' % habits[tid].text)
                except CannotScoreDown as e:
                    print(e)
                    continue
        with_notes = args.full
        for i, task in enumerate(habits):
            score = qualitative_task_score_from_value(task.value)
            updown = {0:' ', 1:'-', 2:'+', 3:'±'}[int(task.can_score_up)*2 + int(task.can_score_down)] # [up][down] as binary number
            print('[{3}|{0}] {1} {2}'.format(score, i + 1, task.text, updown))
            if with_notes:
                print('\n'.join('      {0}'.format(line) for line in task.notes.splitlines()))

    # GET/PUT tasks:daily
    elif args.command == 'dailies':
        user = habitica.user()
        if not user:
            logging.error('Failed to load user dailies')
            return False
        timezoneOffset = user.preferences.timezoneOffset
        dailies = user.dailies()
        if 'done' == args.action:
            tids = get_task_ids(args.task, task_list=dailies)
            for tid in tids:
                item_id = None
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    dailies[tid][item_id].complete()
                    print("marked daily '{0} : {1}' complete".format(dailies[tid].text, dailies[tid][item_id].text))
                else:
                    dailies[tid].complete()
                    print('marked daily \'%s\' completed'
                          % dailies[tid].text)
        elif 'undo' == args.action:
            tids = get_task_ids(args.task, task_list=dailies)
            for tid in tids:
                item_id = None
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    dailies[tid][item_id].undo()
                    print("marked daily '{0} : {1}' incomplete".format(dailies[tid].text, dailies[tid][item_id].text))
                else:
                    dailies[tid].undo()
                    print('marked daily \'%s\' incomplete'
                          % dailies[tid].text)
        print_task_list(dailies, hide_completed=not args.list_all, timezoneOffset=timezoneOffset, with_notes=args.full)

    # GET tasks:todo
    elif args.command == 'todos':
        todos = [e for e in habitica.user.todos() if not e.is_completed]
        if 'done' == args.action:
            tids = get_task_ids(args.task, task_list=todos)
            for tid in tids:
                if isinstance(tid, tuple):
                    tid, item_id = tid
                    todos[tid][item_id].complete()
                    print("marked todo '{0} : {1}' complete".format(todos[tid].text, todos[tid][item_id].text))
                else:
                    todos[tid].complete()
                    print('marked todo \'%s\' complete'
                          % todos[tid].text)
            todos = updated_task_list(todos, tids)
        elif 'add' == args.action: # FIXME not tested and probably not working, should replace with proper creation action.
            ttext = ' '.join(args.task)
            habitica.hbt.tasks(type='todos',
                           text=ttext,
                           priority=PRIORITY[args.difficulty],
                           _method='post')
            todos.insert(0, {'completed': False, 'text': ttext})
            print('added new todo \'%s\'' % ttext)
        with_notes = args.full
        print_task_list(todos, with_notes=args.full)


if __name__ == '__main__':
    cli()
