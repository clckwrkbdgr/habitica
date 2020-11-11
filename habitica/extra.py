import datetime
import html
import logging
from collections import defaultdict
try:
	import markdown
except ImportError:
	markdown = None
	pass

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

class BaseMessageFeed(object):
	""" Basic class for exporting message feed. """
	def add_message(self, group, message):
		""" Adds message to group.

		Expects group as dict:
		- id (string)
		- name (string)

		Expects message as dict:
		- id (string)
		- username (string)
		- timestamp (int)
		- text (original markdown text)
		"""
		raise NotImplementedError
	def done(self):
		""" Finalize feed, dump collected messages etc. """
		raise NotImplementedError

class TextMessageFeed(BaseMessageFeed):
	""" Prints plain text to stdout. """
	def add_message(self, group, message):
		message['group'] = group['name']
		message['timestamp'] = datetime.datetime.fromtimestamp(message['timestamp']),
		print('{group}: {timestamp}: {username}> {text}'.format(**message))

class JsonMessageFeed(BaseMessageFeed):
	""" Dumps json object to stdout. """
	def __init__(self):
		self.json_export = defaultdict(list)
	def add_message(self, group, message):
		self.json_export[group['name']].append(message)
	def done(self):
		print(json.dumps(json_export, indent=2, ensure_ascii=False))

class RSSMessageFeed(BaseMessageFeed):
	""" Dumps RSS feed to stdout. """
	def __init__(self):
		if markdown is None:
			logging.error("Markdown module was not found; will dump messages as text.")
		print(RSS_HEADER)
	def add_message(self, group, message):
		timestamp = str(datetime.datetime.fromtimestamp(message['timestamp']))
		text = '**{username}>** {text}'.format(**message)
		if markdown:
			content = html.escape(markdown.markdown(text))
		else:
			content = '<pre>' + html.escape(text) + '</pre>'
		rss_item = {
				'title' : html.escape(group['name'] + ' ' + timestamp),
				'link' : GROUP_URL.format(id=group['id']),
				'datetime' : timestamp,
				'guid' : message['id'],
				'text' : content,
				}
		print(RSS_ITEM.format(**rss_item))
	def done(self):
		print(RSS_FOOTER)
