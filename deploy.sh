#!/bin/bash 

rsync -a --itemize-changes --progress --exclude "__pycache__" --exclude "*.pyc" --chown www-data:www-data settings.py urls.py uwsgi.ini static/ crossbot/ venv/ /var/www/crossbot/

touch /var/www/crossbot/uwsgi.ini
