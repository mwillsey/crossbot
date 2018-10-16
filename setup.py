#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='crossbot',
    version='0.3',
    description='A bot to help you compete on the NYT mini crossword.',
    author='Max Willsey',
    author_email='me@mwillsey.com',
    url='https://github.com/mwillsey/crossbot',
    packages=find_packages(),
    scripts=['scripts/crossbot-cmd-line.py', 'scripts/crossbot-slack.py'],
)
