# crossbot

A Slack bot to make you really competitive on the New York Times
[mini crossword](http://www.nytimes.com/crosswords/game/mini).

## Installation

Clone the repo and install everything inside a `virtualenv`.
```sh
# clone and enter the repo
git clone git@github.com:mwillsey/crossbot.git
cd crossbot

# create and activate a virtualenv for isolation
virtualenv . --python python3
source bin/activate

# install and setup the package
pip install -r requirements.txt
python setup.py install
```

Initialize the database with `sqlite3 crossbot.db < scripts/init_db.sql` if you don't
have one already.


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
