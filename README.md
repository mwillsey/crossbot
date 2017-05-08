# crossbot

A Slack bot to make you really competitive on the New York Times
[mini crossword](http://www.nytimes.com/crosswords/game/mini).

## Installation

Clone the repo and install everything inside a `virtualenv`.
```sh
git clone git@github.com:mwillsey/crossbot.git
cd crossbot
virtualenv . --python python3
pip install -r requirements.txt
```

Initialize the database with `sqlite3 crossbot.db < init_db.sql` if you don't
have one already.


To actually run the bot, you need to provide an API token.
```sh
export SLACKBOT_API_TOKEN=<<your slack api token>>
python run.py
```

In `slackbot_settings.py` you can change various things including what Slack
user the bot will report errors to.


It's a little difficult to actually test the bot outside of Slack. Your best bet
is to just load `crossbot.py` in a `python` interpreter and call the functions
from there. You'll have to mock up `Message` objects.
