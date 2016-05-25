# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import string_types, text_type

from ..command import Command, Arg, Option
from ..schema import create_schema_from_version, list_available_schema_version, SchemaVersionNotAvailable, ResourceNotDefined, get_last_schema_version
from ..utils import format_tree
from ..exceptions import CommandError


class Schema(Command):
    description = "Explore schema resources"
    schema_version = Option('-v',
                            type=str,
                            default=get_last_schema_version(),
                            help="schema version to use (default='%(default)s')")
    list_version = Option('-l',
                          action="store_true",
                          help="list available schema versions")
    resource_name = Arg(nargs="?", help="Schema resource name",
                        metavar='resource_name')

    def _list_resources(self, schema):
        return "\n".join(schema.all_resources())

    def _resource(self, schema, resource_name):
        try:
            resource = schema.resource(resource_name)
        except ResourceNotDefined as e:
            raise CommandError(text_type(e))
        tree = {
            'node': resource_name,
            'childs': []
        }
        for type in ('parent', 'children', 'refs', 'back_refs'):
            childs = getattr(resource, type)
            if not childs:
                continue
            if isinstance(childs, string_types):
                childs = [childs]
            tree['childs'].append({
                'node': type,
                'childs': [{'node': c} for c in childs]
            })
        return format_tree(tree)

    def __call__(self, schema_version=None,
                 list_version=False, resource_name=None):

        if list_version:
            versions = " ".join(list_available_schema_version())
            return "Available schema versions are: %s" % versions

        else:
            try:
                schema = create_schema_from_version(schema_version)
            except SchemaVersionNotAvailable as e:
                raise CommandError(text_type(e))

            if resource_name is None:
                return self._list_resources(schema)
            else:
                return self._resource(schema, resource_name)
