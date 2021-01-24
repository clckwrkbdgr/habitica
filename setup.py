import os, sys, re
from setuptools import setup, find_packages

with open('README.md') as f: # pragma: no cover
    readme = f.read()

USER_ID_FILE = 'habitica/data/USER_ID'

if not os.path.exists(USER_ID_FILE): # pragma: no cover
    print('File {0} is missing.'.format(USER_ID_FILE))
    print('File {0} should be present in the root directory and should contain Habitica User ID of the author of the package.'.format(USER_ID_FILE))
    print('For forked project it is advisable to use your own User ID (see https://habitica.com/user/settings/api)')
    sys.exit(1)
with open(USER_ID_FILE) as f:
    user_id = f.read().strip()
    if not re.match(r'^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$', user_id, flags=re.I):
        print('File {0} contains invalid user_id: {1}'.format(USER_ID_FILE, repr(user_id)))
        print('Please ensure that proper User ID is used (see https://habitica.com/user/settings/api)')
        sys.exit(1)

setup(
    name='habitica',
    version='0.1.0',
    author='Igor Chaika',
    author_email='clckwrkbdgr@gmail.com',
    url='https://github.com/clckwrkbdgr/habitica',
    license='LICENSE.txt',
    description='Commandline interface to Habitica (http://habitica.com)',
    long_description=readme,
    packages=find_packages(exclude=('dist', 'tests')),
    package_data={
        'habitica': [
            USER_ID_FILE,
            ],
        },
    include_package_data=True,
    install_requires=[
        'requests',
        'vintage',
        'click',
        'click-default-group',
    ],
    entry_points={
        'console_scripts': [
            'habitica = habitica.cli:cli',
            ],
        },
)
