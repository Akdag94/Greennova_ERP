from django.apps import AppConfig


class GreennovaCoreConfig(AppConfig):
    name = 'greennova_core'

    def ready(self):
        from greennova_core import db_signals  # noqa
