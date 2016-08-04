# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Option
from ..utils import to_json
from ..client import ContrailAPISession


class Kv(Command):
    description = "Retrieve the key-value store as json"

    delete = Option("-D", type=str, metavar='key',
                    help="Delete key entry")
    add = Option("-a", nargs=2, metavar=('key', 'value'),
                 help="Add a key and a value")
    get = Option("-g", type=str, metavar='key',
                 help="Get a entry from a key")
    list_all = Option("-l", action="store_true",
                      default=False,
                      help="List all entries")

    def __call__(self, add=None, delete=None, list_all=False, get=None):
        if add is not None:
            ContrailAPISession.session.add_kv_store(add[0], add[1])
            return None
        elif delete is not None:
            ContrailAPISession.session.remove_kv_store(delete)
            return None
        elif get is not None:
            value = ContrailAPISession.session.search_kv_store(get)
            result = [{"key": get,
                       "value": value}]
        elif list_all:
            result = ContrailAPISession.session.get_kv_store()
        else:
            return "Error: One option must be specified.\n\n" + self.parser.format_help()

        return to_json(result)
