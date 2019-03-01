#!/usr/bin/env bash

set -e

rsync="rsync -rz --delete --itemize-changes"

backup="/tmp/crossbot.db.$(date -Iseconds)"
scp uwplse.org:/var/www/crossbot/crossbot.db $backup
echo "Backed up to $backup"

# make sure to include settings/prod.py first, as it's later excluded from .gitignore, and the first pattern wins
$rsync --include settings/prod.py --exclude-from .gitignore --exclude .git . uwplse.org:/var/www/crossbot
