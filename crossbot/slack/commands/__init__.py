# Make these utilities available to commands
from ..parser import date as parse_date
from ..parser import time as parse_time
from ..parser import date_fmt
from ..message import SlashCommandResponse

from ... import models

from settings import DATABASES

# from https://stackoverflow.com/a/3365846
import importlib
import pkgutil

DB_PATH = DATABASES['default']['NAME']

COMMANDS = []
for _, module_name, _ in pkgutil.walk_packages(__path__):
    module_full_name = __name__ + '.' + module_name
    importlib.import_module(module_full_name)
    COMMANDS.append(module_name)
