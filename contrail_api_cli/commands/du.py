# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, expand_paths
from ..resource import Collection
from ..exceptions import NotFound, CommandError


class Du(Command):
    """Count resources of a collection.

    .. code-block:: bash

        admin@localhost:/> du virtual-network
        6
    """
    description = "Count number of resources"
    paths = Arg(nargs="*", help="Collections path(s)", complete='collections::path')
    aliases = ['count = du']

    def __call__(self, paths=None):
        try:
            collections = expand_paths(paths,
                                       predicate=lambda r: isinstance(r, Collection))
        except NotFound:
            raise CommandError("No collection to count")
        result = []
        for c in collections:
            result.append(str(len(c)))
        return "\n".join(result)
