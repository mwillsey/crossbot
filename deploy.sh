#!/bin/bash

set -e

backup="/tmp/crossbot.db.$(date -Iseconds)"
scp uwplse.org:/var/www/crossbot/crossbot.db $backup
echo "Backed up to $backup"
rsync -rz --delete --itemize-changes --progress --exclude-from .gitignore --exclude .git . uwplse.org:/var/www/crossbot
