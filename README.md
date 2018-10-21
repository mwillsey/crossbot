# crossbot
[![Build Status](https://travis-ci.org/mwillsey/crossbot.svg?branch=master)](https://travis-ci.org/mwillsey/crossbot)

A Slack bot to make you really competitive on the New York Times
[mini crossword](http://www.nytimes.com/crosswords/game/mini).

## Developing

Clone the repo and run `make test` to ensure everything works.

There are a few useful `make` targets that are worth knowing about:

- `make venv` will install a virtualenv for with all the dependencies you'll need.
- `make clean` will destroy the virtualenv; use this to update/clean the dependencies
- `make fmt` runs the `yapf` code formatter
- `make check_fmt` checks the formatting using `yapf`
- `make lint[_all_]` runs the `pylint` linter (`lint_all` is very strict)
- `make test` runs the tests
- `make check` runs the formatting check, linter, and tests. This is what the CI runs.
- `make deploy` actually runs the code and not the debug server. You probably don't wanna do this.
