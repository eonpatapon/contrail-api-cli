# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type

from ..resource import Resource
from ..command import Command, Arg, Option, expand_paths
from ..utils import format_table
from ..exceptions import CommandError

RESOURCE_NAME_PATH_SEPARATOR = "."


class Relative(Command):
    description = "Get linked resources by providing a resource name path"
    path = Arg(help="Base resource", metavar='path')
    resource_name_path = Arg(help="Resource names separated by '%s'" % RESOURCE_NAME_PATH_SEPARATOR,
                             metavar='resource_name_path')
    show_intermediate = Option('-l',
                               default=False, action="store_true",
                               help="show intermediate resources")

    def _get_next_resource(self, resource, next_resource_name):
        """
        :param resource: Resource (not necessary fetched)
        :param next_resource_name: string
        :rtype: (resource_type, resource_path)
        """
        resource.fetch()

        # Try to generate the attribute corresponding to the resource type
        type_suffix = {"ref": "_refs", "back_ref": "_back_refs", "child": ""}
        for k, v in type_suffix.items():
            if next_resource_name + v in resource:
                next_resource_attr = next_resource_name + v
                next_resource_type = k
                break
        else:
            raise CommandError("Resource '%s' is not linked to resource type '%s'" %
                               (self.current_path(resource), next_resource_name))

        next_resource = resource.get(next_resource_attr)
        if len(next_resource) > 0:
            return (next_resource_type, next_resource[0])
        else:
            return (None, None)

    def __call__(self, path=None, resource_name_path=None,
                 show_intermediate=False):

        def long_format(resource_type, resource_path):
            return "%8s %s" % (resource_type, resource_path)

        # Get the base resource
        resources = expand_paths([path],
                                 predicate=lambda r: isinstance(r, Resource))
        resource = resources[0]
        resource_type = "base"

        resource_name_paths = resource_name_path.replace('-', '_').split(
            RESOURCE_NAME_PATH_SEPARATOR)

        # Build resources along the path
        result = [(resource_type, resource)]
        for resource_name in resource_name_paths:
            resource_type, resource = self._get_next_resource(
                resource, resource_name)
            result.append((resource_type, resource))

        result = [(t, self.current_path(r)) for t, r in result]
        if show_intermediate:
            return format_table(result)
        else:
            return text_type(result[-1][1])
