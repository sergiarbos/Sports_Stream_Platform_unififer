from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'schedule'

    def ready(self):
        """
        Called once when Django starts. Runs a fast status sync (no API
        calls) so the admin panel is accurate immediately after startup.
        Skipped safely during migrations and tests.
        """
        import threading

        def _sync():
            try:
                from django.db import connection, OperationalError
                # Only run if the DB tables already exist (skip on first migration)
                with connection.cursor() as cursor:
                    tables = connection.introspection.table_names(cursor)
                if 'schedule_event' not in tables:
                    return
                from django.core.management import call_command
                call_command('update_statuses', verbosity=0)
            except Exception:
                pass  # Never crash the server on startup

        # Run in a background thread so startup is not delayed
        t = threading.Thread(target=_sync, daemon=True)
        t.start()
