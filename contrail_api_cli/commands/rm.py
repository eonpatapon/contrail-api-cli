# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, experimental, expand_paths
from ..resource import Resource
from ..utils import continue_prompt


@experimental
class Rm(Command):
    """Delete a resource from the API.

    .. warning::

        `-r` option can be used to delete recursively back_refs of
        the resource.
    """
    description = "Delete a resource"
    paths = Arg(nargs="*", help="Resource path(s)",
                metavar='path', complete="resources::path")
    recursive = Option("-r", action="store_true",
                       default=False,
                       help="Recursive delete of back_refs resources")
    force = Option("-f", action="store_true",
                   default=False,
                   help="Don't ask for confirmation")

    def _get_back_refs(self, resources, back_refs):
        for resource in resources:
            resource.fetch()
            if resource in back_refs:
                back_refs.remove(resource)
            back_refs.append(resource)
            for back_ref in resource.back_refs:
                back_refs = self._get_back_refs([back_ref], back_refs)
        return back_refs

    def __call__(self, paths=None, recursive=False, force=False):
        resources = expand_paths(paths,
                                 predicate=lambda r: isinstance(r, Resource))
        if recursive:
            resources = self._get_back_refs(resources, [])
        if resources:
            message = """About to delete:
 - %s""" % "\n - ".join([self.current_path(r) for r in resources])
            if force or continue_prompt(message=message):
                for r in reversed(resources):
                    print("Deleting %s" % self.current_path(r))
                    r.delete()
