#pylint: disable=wildcard-import,unused-wildcard-import
import os

if os.environ.get('CROSSBOT_PRODUCTION') == '1':
    from settings.prod import *
else:
    from settings.dev import *
