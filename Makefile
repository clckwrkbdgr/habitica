# display project help
help:
	cat README.md | head -n5

# run our roundup tests
test:
	cd habitica; python3 -m doctest core.py

# register with pypi
register:
	python setup.py register

# prepare pypi distribution package
package:
	python setup.py sdist

# distribute on pypi
distribute:
	python setup.py sdist upload
