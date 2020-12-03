import unittest
unittest.defaultTestLoader.testMethodPrefix = 'should'
import textwrap
import requests
from .. import extra

class TestMessageFeeds(unittest.TestCase):
	def _get_messages(self):
		return [
				{
					'id' : 1,
					'timestamp': -2109600,
					'username': 'Mr. Praline',
					'text': "'Ello, I wish to register a complaint.",
					},
				{
					'id' : 2,
					'timestamp': -2109560,
					'username' : 'Mr. Praline',
					'text' : "'Ello, Miss?",
					},
				{

					'id' : 3,
					'timestamp': -2109540,
					'username' : 'Owner',
					'text' : 'What do you mean "miss"?',
					},
				{

					'id' : 4,
					'timestamp': -2109400,
					'username' : 'Mr. Praline',
					'text' : "I'm sorry, I have a cold. I wish to make a complaint!",
					},
				]

	def should_export_feed_as_plain_text(self):
		exporter = extra.TextMessageFeed()
		group = {'id': '1234', 'name' : 'Dead Parrot'}
		for message in self._get_messages():
			exporter.add_message(group, message)
		exporter.done()

		expected = textwrap.dedent("""\
				Dead Parrot: 1969-12-07 17:00:00: Mr. Praline> 'Ello, I wish to register a complaint.
				Dead Parrot: 1969-12-07 17:00:40: Mr. Praline> 'Ello, Miss?
				Dead Parrot: 1969-12-07 17:01:00: Owner> What do you mean "miss"?
				Dead Parrot: 1969-12-07 17:03:20: Mr. Praline> I'm sorry, I have a cold. I wish to make a complaint!
				""")
		self.maxDiff = None
		self.assertEqual(exporter.getvalue(), expected)
	def should_export_feed_as_json(self):
		exporter = extra.JsonMessageFeed()
		group = {'id': '1234', 'name' : 'Dead Parrot'}
		for message in self._get_messages():
			exporter.add_message(group, message)
		exporter.done()

		expected = textwrap.dedent("""\
				{
				  "Dead Parrot": [
				    {
				      "id": 1,
				      "text": "'Ello, I wish to register a complaint.",
				      "timestamp": -2109600,
				      "username": "Mr. Praline"
				    },
				    {
				      "id": 2,
				      "text": "'Ello, Miss?",
				      "timestamp": -2109560,
				      "username": "Mr. Praline"
				    },
				    {
				      "id": 3,
				      "text": "What do you mean \\"miss\\"?",
				      "timestamp": -2109540,
				      "username": "Owner"
				    },
				    {
				      "id": 4,
				      "text": "I'm sorry, I have a cold. I wish to make a complaint!",
				      "timestamp": -2109400,
				      "username": "Mr. Praline"
				    }
				  ]
				}""")
		self.maxDiff = None
		self.assertEqual(exporter.getvalue(), expected)
	def should_export_feed_as_rss(self):
		try:
			import markdown
		except ImportError: # pragma: no cover
			self.fail('Markdown module should be installed for unit tests!')
		exporter = extra.RSSMessageFeed()
		group = {'id': '1234', 'name' : 'Dead Parrot'}
		for message in self._get_messages():
			exporter.add_message(group, message)
		exporter.done()

		expected = textwrap.dedent("""\
				<?xml version="1.0" encoding="UTF-8"?>
				<rss version="2.0">
				<channel>
				<item>
				<title>Dead Parrot 1969-12-07 17:00:00</title>
				<link>https://habitica.com/groups/guild/1234</link>
				<pubDate>1969-12-07 17:00:00</pubDate>
				<guid isPermaLink="false">1</guid>
				<description>&lt;p&gt;&lt;strong&gt;Mr. Praline&amp;gt;&lt;/strong&gt; &#x27;Ello, I wish to register a complaint.&lt;/p&gt;</description>
				</item>
				<item>
				<title>Dead Parrot 1969-12-07 17:00:40</title>
				<link>https://habitica.com/groups/guild/1234</link>
				<pubDate>1969-12-07 17:00:40</pubDate>
				<guid isPermaLink="false">2</guid>
				<description>&lt;p&gt;&lt;strong&gt;Mr. Praline&amp;gt;&lt;/strong&gt; &#x27;Ello, Miss?&lt;/p&gt;</description>
				</item>
				<item>
				<title>Dead Parrot 1969-12-07 17:01:00</title>
				<link>https://habitica.com/groups/guild/1234</link>
				<pubDate>1969-12-07 17:01:00</pubDate>
				<guid isPermaLink="false">3</guid>
				<description>&lt;p&gt;&lt;strong&gt;Owner&amp;gt;&lt;/strong&gt; What do you mean &quot;miss&quot;?&lt;/p&gt;</description>
				</item>
				<item>
				<title>Dead Parrot 1969-12-07 17:03:20</title>
				<link>https://habitica.com/groups/guild/1234</link>
				<pubDate>1969-12-07 17:03:20</pubDate>
				<guid isPermaLink="false">4</guid>
				<description>&lt;p&gt;&lt;strong&gt;Mr. Praline&amp;gt;&lt;/strong&gt; I&#x27;m sorry, I have a cold. I wish to make a complaint!&lt;/p&gt;</description>
				</item>
				
				</channel>
				</rss>
				""")
		self.maxDiff = None
		self.assertEqual(exporter.getvalue(), expected)
