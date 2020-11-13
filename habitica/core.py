from . import api, config

class Habitica:
	""" Main Habitica entry point. """
	def __init__(self, auth=None):
		self.auth = auth
		self.cache = config.Cache()
		self.hbt = api.Habitica(auth=auth)
