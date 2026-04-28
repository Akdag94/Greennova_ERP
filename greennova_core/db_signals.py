"""SQLite WAL modu — bağlantı kurulunca aktif edilir."""
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA foreign_keys=ON;')
        cursor.execute('PRAGMA temp_store=MEMORY;')
