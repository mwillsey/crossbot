#!/usr/bin/env python

from distutils.core import setup

setup(
    name         = 'crossbot',
    version      = '0.3',
    description  = 'A bot to help you compete on the NYT mini crossword.',
    author       = 'Max Willsey',
    author_email = 'me@mwillsey.com',
    url          = 'https://github.com/mwillsey/crossbot',
    packages     = [ 'crossbot', 'crossbot.commands' ],
    scripts      = [ 'scripts/crossbot-cmd-line.py',
                     'scripts/crossbot-slack.py' ],
)
