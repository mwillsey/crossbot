# crossbot
[![Build Status](https://travis-ci.com/mwillsey/crossbot.svg?branch=master)](https://travis-ci.com/mwillsey/crossbot)

A Slack bot to make you really competitive on the New York Times
[mini crossword](http://www.nytimes.com/crosswords/game/mini).

## Installation

Clone the repo and install everything inside a `virtualenv`.
```sh
# clone and enter the repo
git clone git@github.com:mwillsey/crossbot.git
cd crossbot

# this would be a good time to make a virtual environment for isolation
# see below

# make an empty database if you haven't already
# this will *not* overwrite an existing database
sqlite3 crossbot.db < scripts/init_db.sql

# install and setup the package
pip install -r requirements.txt
python setup.py install
```

### Isolation

To create a virtual environment, try
[virtualenvwrapper](http://virtualenvwrapper.readthedocs.io/en/latest/index.html).
The following command will create the virtual environment and immediately use
it.
```sh
mkvirtualenv crossbot --python python3
```

If you don't want to install virtualenvwrapper, you can use plain old
virtualenv. Just make sure to activate it before `pip install`.
```sh
virtualenv . --python python3
source bin/activate
```

## Running the bot

To actually run the bot, you need to provide an API token and use the `slack` subcommand.
```sh
export SLACKBOT_API_TOKEN=<<your slack api token>>
crossbot.py slack
```

There are some settings in `crossbot.py` that you can play with to change, say,
who the errors get reported to.

## Messing around on the command line

You can now run `crossbot` on the command line! Just run `crossbot.py help`
like you normally would on Slack. Pretty much all the functionality works. On
the command line, you're a pretend user with id `command-line-user`.

## Extending crossbot

There's pretty terrible (but somewhat functional) plugin architecture. Files in
`commands/` are automatically loaded. Check out `commands/times.py` to see how a
simple command is implemented. You'll probably want to check out the `Client`
class in `client.py` as well; that's what allows the commands to work the same
over the shell or Slack.

When you're developing, make sure to run `./setup.py install` to get
`crossbot.py` to reflect your changes. If you add or rename files, you might
want to do `./setup.py clean --all` followed by `./setup.py install` to have it
start fresh.
