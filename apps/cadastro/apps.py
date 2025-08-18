from django.apps import AppConfig

class CadastroConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cadastro'   # caminho completo do package
    label = 'cadastro'       # rótulo curto e único