from django.apps import AppConfig


class ArcadeConfig(AppConfig):
    name = "arcade"
    verbose_name = "Oyun (Yılan)"

    def ready(self):
        # user_logged_in alıcısını bağlar (sahipsiz skorların sahiplenilmesi).
        from . import signals  # noqa: F401
