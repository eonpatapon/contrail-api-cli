# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import tempfile
from six import b
import subprocess
import json

from ..command import Command, Arg, Option, expand_paths
from ..resource import Resource
from ..exceptions import CommandError
from ..utils import md5


class Edit(Command):
    """Edit a resource.

    The resource JSON will be opened in an editor. If modifications
    have been made and the file is saved the resource will be sent
    to the API server.

    The `--template` option can be used to create a new resource based
    on an existing resource.
    """
    description = "Edit resource"
    path = Arg(nargs=1, help="Resource path",
               complete='resources::path')
    template = Option('-t',
                      help="Create new resource from existing",
                      action="store_true", default=False)
    aliases = ['vim = edit', 'emacs = edit', 'nano = edit']

    def __call__(self, path=None, template=False):
        resources = expand_paths(path,
                                 predicate=lambda r: isinstance(r, Resource))
        if len(resources) > 1:
            raise CommandError("Can't edit multiple resources")
        resource = resources[0]
        # don't show childs or back_refs
        resource.fetch(exclude_children=True, exclude_back_refs=True)
        resource.pop('id_perms')
        if template:
            resource.pop('href')
            resource.pop('uuid')
        editor = os.environ.get('EDITOR', 'vim')
        with tempfile.NamedTemporaryFile(suffix='tmp.json') as tmp:
            tmp.write(b(resource.json()))
            tmp.flush()
            tmp_md5 = md5(tmp.name)
            subprocess.call([editor, tmp.name])
            tmp.seek(0)
            if tmp_md5 == md5(tmp.name):
                print("No modification made, doing nothing...")
                return
            data_json = tmp.read().decode('utf-8')
        try:
            data = json.loads(data_json)
        except ValueError as e:
            raise CommandError('Provided JSON is not valid: ' + str(e))
        if template:
            # create new resource
            resource = Resource(resource.type, **data)
        else:
            resource.update(data)
        resource.save()
