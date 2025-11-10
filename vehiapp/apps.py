from django.apps import AppConfig


class VehiappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vehiapp'
    def ready(self):
        import vehiapp.signals
