import os
try:
    import ConfigParser as configparser
except:
    import configparser
import logging

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

AUTH_CONF = os.path.join(get_data_dir(), "auth.cfg")

def load_auth(configfile=AUTH_CONF):
	"""Get authentication data from the AUTH_CONF file."""

	logging.debug('Loading habitica auth data from %s' % configfile)

	try:
		with open(configfile) as cf:
			config = configparser.ConfigParser()
			config.read_file(cf)
	except IOError:
		logging.error("Unable to find '%s'." % configfile)
		exit(1)

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

class Cache(object):
	SECTION_CACHE_QUEST = 'Quest'
	configfile = os.path.join(get_cache_dir(), "cache.cfg")

	def __init__(self):
		self.data = None
		self.load()
	def get(self, *args, **kwargs):
		return self.data.get(*args, **kwargs)
	def load(self):
		logging.debug('Loading cached config data (%s)...' % self.configfile)

		defaults = {'quest_key': '',
					'quest_s': 'Not currently on a quest'}

		self.data = configparser.ConfigParser(defaults)
		self.data.read(self.configfile)

		if not self.data.has_section(self.SECTION_CACHE_QUEST):
			self.data.add_section(self.SECTION_CACHE_QUEST)
	def update_quest_cache(self, **kwargs):
		logging.debug('Updating (and caching) config data (%s)...' % self.configfile)

		self.load()

		for key, val in kwargs.items():
			self.data.set(self.SECTION_CACHE_QUEST, key, val)

		with open(self.configfile, 'w') as f:
			self.data.write(f)

		self.data.read(self.configfile)
