import logging


__all__ = ('DatabaseHandler', )


class DatabaseHandler(logging.Handler):
    """Logging handler to store messages in a database"""

    def emit(self, record):
        from openrural.error_log.models import Message
        Message.objects.create(logger=record.name, level=record.levelname,
                               body=record.msg, funcname=record.funcName,
                               pathname=record.pathname, lineno=record.lineno)
