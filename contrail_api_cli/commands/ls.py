# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from six import text_type

from ..command import Command, Arg, Option, expand_paths
from ..resource import Collection, Resource
from ..exceptions import CommandError
from ..utils import format_table


class Ls(Command):
    description = "List resource objects"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path')
    long = Option('-l',
                  default=False, action="store_true",
                  help="use a long listing format")
    column = Option('-c', action="append",
                    help="fields to show in long mode",
                    default=[], dest="fields",
                    metavar="field_name")
    filter = Option('-f', action="append",
                    help="filter predicate",
                    default=[], dest='filters',
                    metavar='field_name=field_value')
    parent_uuid = Option('-P', help="filter by parent uuid")
    # fields to show in -l mode when no
    # column is specified
    default_fields = [u'fq_name']
    aliases = ['ll = ls -l']

    def _field_val_to_str(self, fval, fkey=None):
        if fkey in ('fq_name', 'to'):
            return ":".join(fval)
        elif isinstance(fval, list) or isinstance(fval, Collection):
            return ",".join([self._field_val_to_str(i) for i in fval])
        elif isinstance(fval, dict) or isinstance(fval, Resource):
            return "|".join(["%s=%s" % (k, self._field_val_to_str(v, k))
                             for k, v in fval.items()])
        return text_type(fval)

    def _get_field(self, resource, field):
        # elif field.startswith('.'):
            # value = jq(field).transform(resource.json())
        value = '_'
        if field == 'path':
            value = self.current_path(resource)
        elif hasattr(resource, field):
            value = getattr(resource, field)
        elif isinstance(resource, Resource):
            value = resource.get(field, '_')
        return self._field_val_to_str(value)

    def _get_filter(self, predicate):
        # parse input predicate
        try:
            name, value = predicate.split('=')
        except ValueError:
            raise CommandError('Invalid filter predicate %s. '
                               'Use name=value format.' % predicate)
        if value == 'False':
            value = False
        elif value == 'True':
            value = True
        elif value == 'None':
            value = None
        else:
            try:
                value = int(value)
            except ValueError:
                value = str(value)
        return (name, value)

    def __call__(self, paths=None, long=False, fields=None,
                 filters=None, parent_uuid=None):
        if not long:
            fields = []
        elif not fields:
            fields = self.default_fields
        if filters:
            filters = [self._get_filter(p) for p in filters]
        resources = expand_paths(paths, filters=filters,
                                 parent_uuid=parent_uuid)
        result = []
        for r in resources:
            if isinstance(r, Collection):
                r.fetch(fields=fields)
                result += r.data
            elif isinstance(r, Resource):
                # need to fetch the resource to get needed fields
                if len(fields) > 1 or 'fq_name' not in fields:
                    r.fetch()
                result.append(r)
            else:
                raise CommandError('Not a resource or collection')
        # retrieve asked fields for each resource
        fields = ['path'] + fields
        result = [[self._get_field(r, f) for f in fields] for r in result]
        return format_table(result)
