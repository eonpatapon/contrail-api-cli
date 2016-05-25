# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from ..command import Command, Arg, Option, expand_paths
from ..exceptions import CommandError
from ..resource import Resource
from ..schema import create_schema_from_version, SchemaVersionNotAvailable, ResourceNotDefined, get_last_schema_version


class Ln(Command):
    description = "Link two resources"
    resources = Arg(help='resource to link', metavar='PATH', nargs=2)
    remove = Option('-r', help='remove link',
                    action='store_true', default=False)
    schema_version = Option('-v',
                            type=str,
                            default=get_last_schema_version(),
                            help="schema version to use (default='%(default)s')")

    def __call__(self, resources=None, remove=None, schema_version=None):
        try:
            schema = create_schema_from_version(schema_version)
        except SchemaVersionNotAvailable as e:
            raise CommandError(text_type(e))

        for idx, r in enumerate(resources):
            resources[idx] = expand_paths([r],
                                          predicate=lambda r: isinstance(r, Resource))[0]

        res1, res2 = resources

        try:
            res1_schema = schema.resource(res1.type)
        except ResourceNotDefined as e:
            raise CommandError(text_type(e))

        if res2.type in res1_schema.refs:
            if remove:
                res1.remove_ref(res2)
            else:
                res1.add_ref(res2)
        elif res2.type in res1_schema.back_refs:
            if remove:
                res1.remove_back_ref(res2)
            else:
                res1.add_back_ref(res2)
        else:
            raise CommandError("Can't link %s with %s" % (self.current_path(res1),
                                                          self.current_path(res2)))
