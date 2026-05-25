from django.apps import AppConfig


class UserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user'

    def ready(self):
        import os

        if os.environ.get('RUN_MAIN') != 'true':
            return

        from .schedule import start_scheduler
        start_scheduler()