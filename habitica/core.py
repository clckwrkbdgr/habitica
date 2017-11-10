#!/usr/bin/env python
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
from time import sleep
from webbrowser import open_new_tab

from docopt import docopt

try:
    from . import api
except SystemError:
    pass # to allow import for doctest
except ValueError:
    pass # to allow import for doctest

from pprint import pprint

try:
    import ConfigParser as configparser
except:
    import configparser

def dump_json(obj, filename):
    with open(filename, 'wb') as f:
        f.write(json.dumps(obj, indent=4, ensure_ascii=False).encode('utf-8'))

def load_json(filename):
    with open(filename, 'rb') as f:
        return json.loads(f.read().decode('utf-8'))

def get_data_dir(*args):
    xdg_data_dir = os.environ.get('XDG_DATA_HOME')
    if not xdg_data_dir:
        xdg_data_dir = os.path.join(os.path.expanduser("~"), ".local", "share")
    app_data_dir = os.path.join(xdg_data_dir, "habitica")
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

def get_cache_dir(*args):
    xdg_cache_dir = os.environ.get('XDG_CACHE_HOME')
    if not xdg_cache_dir:
        xdg_cache_dir = os.path.join(os.path.expanduser("~"), ".cache")
    app_cache_dir = os.path.join(xdg_cache_dir, "habitica")
    os.makedirs(app_cache_dir, exist_ok=True)
    return app_cache_dir


VERSION = 'habitica version 0.0.12'
TASK_VALUE_BASE = 0.9747  # http://habitica.wikia.com/wiki/Task_Value
HABITICA_REQUEST_WAIT_TIME = 0.5  # time to pause between concurrent requests
HABITICA_TASKS_PAGE = '/#/tasks'
# https://trello.com/c/4C8w1z5h/17-task-difficulty-settings-v2-priority-multiplier
PRIORITY = {'easy': 1,
            'medium': 1.5,
            'hard': 2}
AUTH_CONF = os.path.join(get_data_dir(), "auth.cfg")
CACHE_CONF = os.path.join(get_cache_dir(), "cache.cfg")

SECTION_CACHE_QUEST = 'Quest'

GROUP_URL = 'https://habitica.com/groups/guild/{id}'
RSS_HEADER = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
"""
# {title, link, datetime, guid, text}
RSS_ITEM = """<item>
<title>{title}</title>
<link>{link}</link>
<pubDate>{datetime}</pubDate>
<guid isPermaLink="false">{guid}</guid>
<description>{text}</description>
</item>"""
RSS_FOOTER = """
</channel>
</rss>
"""

def load_auth(configfile):
    """Get authentication data from the AUTH_CONF file."""

    logging.debug('Loading habitica auth data from %s' % configfile)

    try:
        cf = open(configfile)
    except IOError:
        logging.error("Unable to find '%s'." % configfile)
        exit(1)

    config = configparser.SafeConfigParser()
    config.readfp(cf)

    cf.close()

    # Get data from config
    rv = {}
    try:
        rv = {'url': config.get('Habitica', 'url'),
              'x-api-user': config.get('Habitica', 'login'),
              'x-api-key': config.get('Habitica', 'password')}

    except configparser.NoSectionError:
        logging.error("No 'Habitica' section in '%s'" % configfile)
        exit(1)

    except configparser.NoOptionError as e:
        logging.error("Missing option in auth file '%s': %s"
                      % (configfile, e.message))
        exit(1)

    # Return auth data as a dictionnary
    return rv


def load_cache(configfile):
    logging.debug('Loading cached config data (%s)...' % configfile)

    defaults = {'quest_key': '',
                'quest_s': 'Not currently on a quest'}

    cache = configparser.SafeConfigParser(defaults)
    cache.read(configfile)

    if not cache.has_section(SECTION_CACHE_QUEST):
        cache.add_section(SECTION_CACHE_QUEST)

    return cache


def update_quest_cache(configfile, **kwargs):
    logging.debug('Updating (and caching) config data (%s)...' % configfile)

    cache = load_cache(configfile)

    for key, val in kwargs.items():
        cache.set(SECTION_CACHE_QUEST, key, val)

    with open(configfile, 'w') as f:
        cache.write(f)

    cache.read(configfile)

    return cache

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

class LocalTZ(datetime.tzinfo):
    STDOFFSET = datetime.timedelta(seconds = -time.timezone)
    DSTOFFSET = datetime.timedelta(seconds = -time.altzone) if time.daylight else STDOFFSET
    DSTDIFF = DSTOFFSET - STDOFFSET
    def utcoffset(self, dt):
        if self._isdst(dt):
            return LocalTZ.DSTOFFSET
        else:
            return LocalTZ.STDOFFSET
    def dst(self, dt):
        if self._isdst(dt):
            return LocalTZ.DSTDIFF
        else:
            return datetime.timedelta(0)
    def tzname(self, dt):
        return time.tzname[self._isdst(dt)]
    def _isdst(self, dt):
        tt = (dt.year, dt.month, dt.day,
              dt.hour, dt.minute, dt.second,
              dt.weekday(), 0, 0)
        stamp = time.mktime(tt)
        tt = time.localtime(stamp)
        return tt.tm_isdst > 0

def strptime_habitica_to_local(time_string):
    ''' Habitica's task start time is in GMT (apparently?)
    so it needs to be converted to local TZ before calculating any task repetition.
    '''
    return datetime.datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=datetime.timezone.utc).astimezone(LocalTZ())

def parse_isodate(isodate):
    return datetime.datetime.strptime(isodate, "%Y-%m-%d %H:%M:%S.%f")

def days_passed(habitica_startDate, localnow, timezoneOffset=0):
    """
    >>> days_passed('2016-06-20T21:00:00.000Z', parse_isodate('2016-11-08 16:51:15.930842'), timezoneOffset=-120)
    141
    >>> days_passed('2016-06-20T21:00:00.000Z', parse_isodate('2016-11-08 20:51:15.930842'), timezoneOffset=-120)
    141
    >>> days_passed('2016-06-20T21:00:00.000Z', parse_isodate('2016-11-08 21:51:15.930842'), timezoneOffset=-120)
    141
    >>> days_passed('2016-06-20T21:00:00.000Z', parse_isodate('2016-11-09 16:51:15.930842'), timezoneOffset=-120)
    142
    >>> days_passed('2015-07-01T16:50:07.000Z', parse_isodate('2016-10-23 16:51:15.930842'), timezoneOffset=-120)
    480
    >>> days_passed('2015-07-01T16:50:07.000Z', parse_isodate('2016-10-23 15:51:15.930842'), timezoneOffset=-120)
    480
    >>> days_passed('2015-07-01T16:50:07.000Z', parse_isodate('2016-10-23 21:51:15.930842'), timezoneOffset=-120)
    480
    >>> days_passed('2016-01-01T20:39:15.833Z', parse_isodate('2016-11-06 21:51:15.930842'), timezoneOffset=-120)
    310
    >>> days_passed('2016-01-01T20:39:15.833Z', parse_isodate('2016-11-06 20:31:15.930842'), timezoneOffset=-120)
    310
    >>> days_passed('2016-01-01T20:39:15.833Z', parse_isodate('2016-11-06 15:31:15.930842'), timezoneOffset=-120)
    310
    >>> days_passed('2016-12-30T22:00:00.000Z', parse_isodate('2017-01-03 19:46:59.290457'), timezoneOffset=-120)
    3
    """
    #startdate = strptime_habitica_to_local(habitica_startDate)
    startdate = datetime.datetime.strptime(habitica_startDate, '%Y-%m-%dT%H:%M:%S.%fZ')
    startdate -= datetime.timedelta(minutes=timezoneOffset)
    currentdate = localnow
    return (currentdate.date() - startdate.date()).days

def print_task_list(tasks, hide_completed=False, timezoneOffset=0):
    for i, task in enumerate(tasks):
        if 'type' in task and task['type'] == 'daily':
            if task['frequency'] == 'daily':
                if days_passed(task['startDate'], datetime.datetime.now(), timezoneOffset=timezoneOffset) % task['everyX'] != 0:
                    continue
            elif task['frequency'] == 'weekly':
                habitica_week = ["m", "t", "w", "th", "f", "s", "su"]
                if not task['repeat'][habitica_week[datetime.datetime.now().weekday()]]:
                    continue
            else:
                print("Unknown daily frequency: {0}".format(task['frequency']))
        completed = 'x' if task['completed'] else ' '
        if task['completed'] and hide_completed:
            continue
        print('[%s] %s %s' % (completed, i + 1, task['text']))
        for j, item in enumerate(task['checklist']):
            completed = 'x' if item['completed'] else ' '
            print('    [%s] %s.%s %s' % (completed, i + 1, j + 1, item['text']))

def qualitative_task_score_from_value(value):
    # task value/score info: http://habitica.wikia.com/wiki/Task_Value
    scores = ['<<<   ', ' <<   ', '  <   ', '      ', '   >  ', '   >> ', '   >>>']
    breakpoints = [-20, -10, -1, 1, 5, 10]
    return scores[bisect(breakpoints, value)]


def cli():
    """Habitica command-line interface.

    Usage: habitica [--version] [--help]
                    <command> [<args>...] [--list-all] [--difficulty=<d>]
                    [--seen] [--json] [--rss]
                    [--verbose | --debug]

    Options:
      -h --help         Show this screen
      --version         Show version
      --difficulty=<d>  (easy | medium | hard) [default: easy]
      --verbose         Show some logging information
      --debug           Show all logging information
      --list-all        List all dailies. By default only
                        not done dailies will be displayed

    The habitica commands are:
      status                 Show HP, XP, GP, and more
      habits                 List habit tasks
      habits up <task-id>    Up (+) habit <task-id>
      habits down <task-id>  Down (-) habit <task-id>
      dailies                List daily tasks
      dailies done           Mark daily <task-id> complete
      dailies undo           Mark daily <task-id> incomplete
      todos                  List todo tasks
      todos done <task-id>   Mark one or more todo <task-id> completed
      todos add <task>       Add todo with description <task>
      health                 Buy health potion
      spells                 List available spells
      messages [<count>] [--seen] [--json] [--rss]
                             Lists last <count> messages for all guilds user is in.
           <count>           Max count of messages displayed, if 0 (default) displays all.
           --seen            Mark all messages as read.
           --json            Print all messages in JSON format.
           --rss             Print all messages in RSS format.
      server                 Show status of Habitica service
      home                   Open tasks page in default browser

    For `habits up|down`, `dailies done|undo`, and `todos done`, you can pass
    one or more <task-id> parameters, using either comma-separated lists or
    ranges or both. For example, `todos done 1,3,6-9,11`.
    """

    # set up args
    args = docopt(cli.__doc__, version=VERSION)

    # set up logging
    if args['--verbose']:
        logging.basicConfig(level=logging.INFO)
    if args['--debug']:
        logging.basicConfig(level=logging.DEBUG)

    logging.debug('Command line args: {%s}' %
                  ', '.join("'%s': '%s'" % (k, v) for k, v in args.items()))

    # Set up auth
    auth = load_auth(AUTH_CONF)

    # Prepare cache
    cache = load_cache(CACHE_CONF)

    # instantiate api service
    hbt = api.Habitica(auth=auth)

    # GET server status
    if args['<command>'] == 'server':
        server = hbt.status()
        if server['status'] == 'up':
            print('Habitica server is up')
        else:
            print('Habitica server down... or your computer cannot connect')

    # open HABITICA_TASKS_PAGE
    elif args['<command>'] == 'home':
        home_url = '%s%s' % (auth['url'], HABITICA_TASKS_PAGE)
        print('Opening %s' % home_url)
        open_new_tab(home_url)

    # messages
    elif args['<command>'] == 'messages':
        mark_as_seen = args['--seen']
        as_json = args['--json']
        as_rss = args['--rss']
        if as_json and as_rss:
            print('Only one type of export could be specified: --rss, --json')
            sys.exit(1)
        max_count = 0 # By default no restriction - print all messages.
        if args['<args>']:
            max_count = int(args['<args>'][0])

        groups = hbt.groups(type='guilds')
        groups.extend(hbt.groups(type='party'))
        json_export = {}
        if as_rss:
            print(RSS_HEADER)
        for group in groups:
            group_name = group['name']
            chat_messages = hbt.groups[group['id']].chat()
            json_export[group_name] = []
            if max_count:
                chat_messages = chat_messages[:max_count]
            for entry in chat_messages:
                message = {
                        'username': entry['user'] if 'user' in entry else 'system',
                        'timestamp': int(int(entry['timestamp']) / 1000),
                        'text': entry['text'],
                        }
                message['text'] = '{username}> {text}'.format(**message)
                if as_json:
                    json_export[group_name].append(message)
                elif as_rss:
                    timestamp = str(datetime.datetime.fromtimestamp(message['timestamp']))
                    rss_item = {
                            'title' : html.escape(group_name + ' ' + timestamp),
                            'link' : GROUP_URL.format(id=group['id']),
                            'datetime' : timestamp,
                            'guid' : entry['id'],
                            'text' : html.escape(message['text']),
                    }
                    print(RSS_ITEM.format(**rss_item))
                else:
                    message['group'] = group_name
                    message['timestamp'] = datetime.datetime.fromtimestamp(message['timestamp']),
                    print('{group}: {timestamp}: {username}> {text}'.format(**message))
            if mark_as_seen:
                hbt.groups[group['id']]['chat'].seen(_method='post')
        if as_json:
            print(json.dumps(json_export, indent=2, ensure_ascii=False))
        elif as_rss:
            print(RSS_FOOTER)

    # GET user
    elif args['<command>'] == 'status':

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

            if cache.get(SECTION_CACHE_QUEST, 'quest_key') != quest_key:
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
                cache = update_quest_cache(CACHE_CONF,
                                           quest_key=str(quest_key),
                                           quest_type=str(quest_type),
                                           quest_max=str(quest_max),
                                           quest_title=str(quest_title))

            # now we use /party and quest_type to figure out our progress!
            quest_type = cache.get(SECTION_CACHE_QUEST, 'quest_type')
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
                    cache.get(SECTION_CACHE_QUEST, 'quest_max'),
                    cache.get(SECTION_CACHE_QUEST, 'quest_title'))

        # prepare and print status strings
        title = 'Level %d %s' % (stats['lvl'], stats['class'].capitalize())
        health = '%d/%d' % (stats['hp'], stats['maxHealth'])
        xp = '%d/%d' % (int(stats['exp']), stats['toNextLevel'])
        mana = '%d/%d' % (int(stats['mp']), stats['maxMP'])
        currentPet = items.get('currentPet', '')
        pet = '%s (%d food items)' % (currentPet, food_count)
        mount = items.get('currentMount', '')
        summary_items = ('health', 'xp', 'mana', 'quest', 'pet', 'mount')
        len_ljust = max(map(len, summary_items)) + 1
        print('-' * len(title))
        print(title)
        print('-' * len(title))
        print('%s %s' % ('Health:'.rjust(len_ljust, ' '), health))
        print('%s %s' % ('XP:'.rjust(len_ljust, ' '), xp))
        print('%s %s' % ('Mana:'.rjust(len_ljust, ' '), mana))
        print('%s %s' % ('Pet:'.rjust(len_ljust, ' '), pet))
        print('%s %s' % ('Mount:'.rjust(len_ljust, ' '), mount))
        print('%s %s' % ('Quest:'.rjust(len_ljust, ' '), quest))

    # POST buy health potion
    elif args['<command>'] == 'health':
        HEALTH_POTION_VALUE = 15.0
        user = hbt.user()
        stats = user.get('stats', '')
        if stats['hp'] + HEALTH_POTION_VALUE > stats['maxHealth']:
            print('HP is too high, part of health potion would be wasted.')
            print('HP: {0:.1f}/{1}, need at most {2:.1f}'.format(stats['hp'], stats['maxHealth'], stats['maxHealth'] - HEALTH_POTION_VALUE))
        else:
            new_stats = hbt.user['buy-health-potion'](_method='post')
            print('Bought Health Potion, HP: {0:.1f}/{1}'.format(new_stats['hp'], stats['maxHealth']))

    # list/POST spells
    elif args['<command>'] == 'spells':
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
        if args['<args>']:
            spell_name, targets = args['<args>'][0], args['<args>'][1:]
            if spell_name not in SPELLS[user_class]:
                print('{1} cannot cast spell {0}'.format(user_class.title(), spell_name))
            else:
                hbt.user['class']['cast'][spell_name](_method='post')
                print('Casted spell "{0}"'.format(SPELLS[user_class][spell_name]))
        else:
            for name, description in SPELLS[user_class].items():
                print('{0} - {1}'.format(name, description))

    # GET/POST habits
    elif args['<command>'] == 'habits':
        habits = hbt.tasks.user(type='habits')
        if 'up' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:], task_list=habits)
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
        elif 'down' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:], task_list=habits)
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
        for i, task in enumerate(habits):
            score = qualitative_task_score_from_value(task['value'])
            updown = {0:' ', 1:'-', 2:'+', 3:'±'}[int(task['up'])*2 + int(task['down'])] # [up][down] as binary number
            print('[{3}|{0}] {1} {2}'.format(score, i + 1, task['text'], updown))

    # GET/PUT tasks:daily
    elif args['<command>'] == 'dailies':
        user = hbt.user()
        timezoneOffset = user['preferences']['timezoneOffset']
        dailies = hbt.tasks.user(type='dailys')
        if 'done' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:], task_list=dailies)
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
        elif 'undo' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:], task_list=dailies)
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
        print_task_list(dailies, hide_completed=not args['--list-all'], timezoneOffset=timezoneOffset)

    # GET tasks:todo
    elif args['<command>'] == 'todos':
        todos = [e for e in hbt.tasks.user(type='todos')
                 if not e['completed']]
        if 'done' in args['<args>']:
            tids = get_task_ids(args['<args>'][1:], task_list=todos)
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
        elif 'add' in args['<args>']:
            ttext = ' '.join(args['<args>'][1:])
            hbt.tasks(type='todos',
                           text=ttext,
                           priority=PRIORITY[args['--difficulty']],
                           _method='post')
            todos.insert(0, {'completed': False, 'text': ttext})
            print('added new todo \'%s\'' % ttext)
        print_task_list(todos)


if __name__ == '__main__':
    cli()
