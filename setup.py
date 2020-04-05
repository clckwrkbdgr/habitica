from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

setup(
    name='habitica',
    version='0.0.12',
    author='Phil Adams',
    author_email='philadams.net@gmail.com',
    url='https://github.com/philadams/habitica',
    license='LICENSE.txt',
    description='Commandline interface to Habitica (http://habitica.com)',
    long_description=readme,
    packages=find_packages(exclude=('dist', 'tests')),
    install_requires=[
        'requests',
    ],
    scripts=['bin/habitica'],
)
