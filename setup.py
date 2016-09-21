#!/usr/bin/env python
"""GoPubBot.

Pub Telegram bot.
"""

from setuptools import setup, find_packages


VERSION = '0.1.0.dev0'

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='gopubbot',
    version=VERSION,
    url='https://github.com/priver/gopubbot',
    author='Mikhail Priver',
    author_email='m.priver@gmail.com',
    description='Pub Telegram bot.',
    long_description=open('README.md').read(),
    license='MIT',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': 'gopubbot = gopubbot.app:run'
    },
    install_requires=requirements,
    zip_safe=False,
)
