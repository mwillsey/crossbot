
activate = . venv/bin/activate

.PHONY: migrate kill

venv:
	virtualenv --quiet --python python3 --no-site-packages $@
	${activate} && pip install --quiet -r requirements.txt

static: venv
	${activate} && ./manage.py collectstatic --no-input

migrate: venv
	${activate} && ./manage.py migrate

test: venv
	${activate} && ./manage.py test

kill:
	kill `cat /tmp/crossbot.pid` || true

run: kill venv static migrate
	${activate} && gunicorn --daemon --workers 4 --pid /tmp/crossbot.pid --bind "unix:/tmp/crossbot.sock" "wsgi:application"
