# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import add_metaclass

from .utils import Singleton


class SchemaNotInitialized(Exception):
    pass


@add_metaclass(Singleton)
class Context(object):
    _schema = None

    @property
    def schema(self):
        if self._schema is None:
            raise SchemaNotInitialized("The schema must be fisrt initialized")
        else:
            return self._schema

    @schema.setter
    def schema(self, schema):
        self._schema = schema
