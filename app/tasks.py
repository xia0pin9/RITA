from __future__ import absolute_import

from app.ht_celery import celery

@celery.task
def RunImporter(ImporterFunc):
    ImporterFunc()
    return
