from django.apps import AppConfig


class ScheduleConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "schedule"

    def ready(self):
        """
        Called once when Django starts. Two things happen:
        1. Fast status sync (no API calls) so the admin is accurate on startup.
        2. Import schedule.tasks to register Huey periodic tasks.
        Both are skipped safely during migrations/tests.
        """
        import threading

        def _sync():
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    tables = connection.introspection.table_names(cursor)
                if "schedule_event" not in tables:
                    return
                from django.core.management import call_command

                call_command("update_statuses", verbosity=0)
            except Exception:
                pass  # Never crash the server on startup

        # Run in a background thread so startup is not delayed
        t = threading.Thread(target=_sync, daemon=True)
        t.start()

        # Register Huey periodic tasks (safe to import even outside worker)
        try:
            import schedule.tasks  # noqa: F401
        except Exception:
            pass
