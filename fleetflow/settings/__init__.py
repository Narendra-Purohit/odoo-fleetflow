# Delegate to development settings by default.
# To use production: set DJANGO_SETTINGS_MODULE=fleetflow.settings.prod
from fleetflow.settings.dev import *  # noqa: F401, F403
