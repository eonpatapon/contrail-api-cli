# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, expand_paths
from ..resource import Resource
from ..utils import highlight_json


class Cat(Command):
    description = "Print a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path', complete='resources::path')

    def __call__(self, paths=None):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        result = []
        for r in resources:
            r.fetch()
            json_data = r.json()
            if self.is_piped:
                result.append(json_data)
            else:
                result.append(highlight_json(json_data))
        return "".join(result)
