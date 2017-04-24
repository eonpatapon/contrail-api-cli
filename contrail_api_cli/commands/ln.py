# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from ..command import Command, Arg, Option, expand_paths
from ..exceptions import CommandError
from ..resource import Resource
from ..schema import require_schema


class Ln(Command):
    """Add or remove a reference link between two resources.

    .. code-block:: bash

        admin@localhost:/> tree -r /virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7
        virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7                default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2
        ├── virtual-machine-interface/d739db3d-b89f-46a4-ae02-97ac796261d0  default-domain:foo:default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2__right__1
        │   ├── floating-ip/958234f5-4fae-4afd-ae7c-d0dc3c608e06            default-domain:admin:public:floating-ip-pool:958234f5-4fae-4afd-ae7c-d0dc3c608e06
        │   └── instance-ip/bced2a04-0ef9-4c87-95a6-7cce54182c65            7d401b8c-b9d3-4be2-af0b-a0dfff500860
        └── virtual-router/f6f0b262-745b-45f7-a40a-32ffc1f469bc             default-global-system-config:vrouter-1
        admin@localhost:/> ln -r virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7 virtual-router/f6f0b262-745b-45f7-a40a-32ffc1f469bc
        admin@localhost:/> tree -r /virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7
        virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7                default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2
        └── virtual-machine-interface/d739db3d-b89f-46a4-ae02-97ac796261d0  default-domain:foo:default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2__right__1
            ├── floating-ip/958234f5-4fae-4afd-ae7c-d0dc3c608e06            default-domain:admin:public:floating-ip-pool:958234f5-4fae-4afd-ae7c-d0dc3c608e06
            └── instance-ip/bced2a04-0ef9-4c87-95a6-7cce54182c65            7d401b8c-b9d3-4be2-af0b-a0dfff500860
        admin@localhost:/> ln virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7 virtual-router/f6f0b262-745b-45f7-a40a-32ffc1f469bc
        admin@localhost:/> tree -r /virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7
        virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7                default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2
        ├── virtual-machine-interface/d739db3d-b89f-46a4-ae02-97ac796261d0  default-domain:foo:default-domain__foo__fa3ea892-3591-4611-ba22-cc45164aee3e__2__right__1
        │   ├── floating-ip/958234f5-4fae-4afd-ae7c-d0dc3c608e06            default-domain:admin:public:floating-ip-pool:958234f5-4fae-4afd-ae7c-d0dc3c608e06
        │   └── instance-ip/bced2a04-0ef9-4c87-95a6-7cce54182c65            7d401b8c-b9d3-4be2-af0b-a0dfff500860
        └── virtual-router/f6f0b262-745b-45f7-a40a-32ffc1f469bc             default-global-system-config:vrouter-1
    """
    description = "Link two resources"
    resources = Arg(help='resource to link', metavar='PATH', nargs=2,
                    complete='resources::path')
    remove = Option('-r', help='remove link',
                    action='store_true', default=False)

    @require_schema()
    def __call__(self, resources=None, remove=None, schema_version=None):
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
