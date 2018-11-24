from django.conf import settings as s

# Placing crossbot settings in here for now
CROSSBUCKS_PER_SOLVE = getattr(s, 'CROSSBOT_CROSSBUCKS_PER_SOLVE', 10)
ITEM_DROP_RATE = getattr(s, 'CROSSBOT_ITEM_DROP_RATE', 0.1)
DEFAULT_TITLE = getattr(s, 'CROSSBOT_DEFAULT_TITLE', "Crossworder")
