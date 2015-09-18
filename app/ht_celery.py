from __future__ import absolute_import

from celery import Celery

celery = Celery('app',
        broker='amqp://',
        backend='amqp://',
        include=['app.tasks'])

celery.conf.update(
        CELERY_TASK_RESULT_EXPIRES=3600,
        )

if __name__ == '__main__':
    celery.start()
