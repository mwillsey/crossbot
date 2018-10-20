from django.conf import settings as s

# Placing crossbot settings in here for now
CROSSBUCKS_PER_SOLVE = getattr(s, 'CROSSBOT_CROSSBUCKS_PER_SOLVE', 10)
