# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import add_metaclass

from .utils import Singleton


@add_metaclass(Singleton)
class Context(object):
    _schema = None

    @property
    def schema(self):
        return self._schema

    @schema.setter
    def schema(self, schema):
        self._schema = schema
