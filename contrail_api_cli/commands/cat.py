# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, expand_paths
from ..resource import Resource
from ..utils import highlight_json


class Cat(Command):
    """Print resource details in json format.

    .. code-block:: bash

        admin@localhost:/> cat instance-ip/2f5c047d-0a9c-4709-bcfa-d710ac68cc22
        {
          "display_name": "2f5c047d-0a9c-4709-bcfa-d710ac68cc22",
          "fq_name": [
            "2f5c047d-0a9c-4709-bcfa-d710ac68cc22"
          ],
          "href": "http://localhost:8082/instance-ip/2f5c047d-0a9c-4709-bcfa-d710ac68cc22",
          "instance_ip_address": "192.168.10.3",
          "instance_ip_family": "v4",
          "name": "2f5c047d-0a9c-4709-bcfa-d710ac68cc22",
          "subnet_uuid": "96b51c74-090b-4c3e-9f73-ecd8efac294d",
          "uuid": "2f5c047d-0a9c-4709-bcfa-d710ac68cc22",
          [...]
        }
    """
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
