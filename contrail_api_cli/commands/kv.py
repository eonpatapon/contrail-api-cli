# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Option
from ..utils import to_json, highlight_json
from ..context import Context


class Kv(Command):
    """Command to interact with the key-value store.

    .. code-block:: bash

        admin@localhost:/> kv --add my-key my-value
        admin@localhost:/> kv --get my-key
        [
          {
            "key": "my-key",
            "value": "my-value"
          }
        ]

        admin@localhost:/> kv --delete my-key
        admin@localhost:/> kv --get my-key
        Unknown User-Agent key my-key (HTTP 404)
    """
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
            Context().session.add_kv_store(add[0], add[1])
            return None
        elif delete is not None:
            Context().session.remove_kv_store(delete)
            return None
        elif get is not None:
            value = Context().session.search_kv_store(get)
            result = [{"key": get,
                       "value": value}]
        elif list_all:
            result = Context().session.get_kv_store()
        else:
            return "Error: One option must be specified.\n\n" + self.parser.format_help()

        if self.is_piped:
            return to_json(result)
        else:
            return highlight_json(to_json(result))
