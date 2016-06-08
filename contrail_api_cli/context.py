# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import add_metaclass

from .utils import Singleton, Path


class SchemaNotInitialized(Exception):
    pass


class ShellContext(object):
    current_path = Path("/")


@add_metaclass(Singleton)
class Context(object):
    _schema = None
    _shell = ShellContext

    @property
    def schema(self):
        if self._schema is None:
            raise SchemaNotInitialized("The schema must be first initialized")
        else:
            return self._schema

    @schema.setter
    def schema(self, schema):
        self._schema = schema

    @property
    def shell(self):
        return self._shell
