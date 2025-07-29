from django.apps import AppConfig


class FightersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'fighters'
    verbose_name = 'Fighter Management'
    
    def ready(self):
        """Initialize app when Django starts"""
        # Import signals here if needed
        pass