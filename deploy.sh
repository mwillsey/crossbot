#!/bin/bash

rsync -rz --delete --itemize-changes --progress --exclude-from .gitignore --exclude .git . uwplse.org:/var/www/crossbot
