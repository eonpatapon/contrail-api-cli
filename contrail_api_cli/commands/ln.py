# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..exceptions import CommandError
from ..resource import Resource
from ..context import Context
from ..schema import DummySchema


class Ln(Command):
    description = "Link two resources"
    resources = Arg(help='resource to link', metavar='PATH', nargs=2)
    remove = Option('-r', help='remove link',
                    action='store_true', default=False)

    def __call__(self, resources=None, remove=None, schema_version=None):
        if isinstance(Context().schema, DummySchema):
            raise CommandError("Can't use ln without specifying a schema version")

        for idx, r in enumerate(resources):
            resources[idx] = expand_paths([r],
                                          predicate=lambda r: isinstance(r, Resource))[0]

        res1, res2 = resources

        if res2.type in res1.schema.refs:
            if remove:
                res1.remove_ref(res2)
            else:
                res1.add_ref(res2)
        elif res2.type in res1.schema.back_refs:
            if remove:
                res1.remove_back_ref(res2)
            else:
                res1.add_back_ref(res2)
        else:
            raise CommandError("Can't link %s with %s" % (self.current_path(res1),
                                                          self.current_path(res2)))
