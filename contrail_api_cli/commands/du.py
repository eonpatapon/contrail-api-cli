# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, expand_paths
from ..resource import Collection


class Du(Command):
    description = "Count number of resources"
    paths = Arg(nargs="*", help="Resource path(s)")

    def __call__(self, paths=None):
        collections = expand_paths(paths,
                                   predicate=lambda r: isinstance(r, Collection))
        result = []
        for c in collections:
            result.append(str(len(c)))
        return "\n".join(result)
