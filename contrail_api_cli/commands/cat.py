# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pygments import highlight
from pygments.lexers import JsonLexer
from pygments.formatters import Terminal256Formatter

from ..command import Command, Arg, expand_paths
from ..resource import Resource


class Cat(Command):
    description = "Print a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')

    def colorize(self, json_data):
        return highlight(json_data,
                         JsonLexer(indent=2),
                         Terminal256Formatter(bg="dark"))

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
                result.append(self.colorize(json_data))
        return "".join(result)
