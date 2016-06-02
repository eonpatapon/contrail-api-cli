# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from six import text_type
import re

from ..resource import Resource
from ..command import Command, Arg, Option, expand_paths
from ..utils import format_table
from ..exceptions import CommandError

RESOURCE_NAME_PATH_SEPARATOR = "/"


class Relative(Command):
    """Find linked resource using a resource-type path.

    .. code-block:: bash

        admin@localhost:/> relative virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7 virtual-machine-interface/floating-ip
        floating-ip/958234f5-4fae-4afd-ae7c-d0dc3c608e06
        admin@localhost:/> relative -l virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7 virtual-machine-interface/floating-ip
        base      virtual-machine/8cfbddcf-6b55-4cdf-abcb-14eed68e4da7
        back_ref  virtual-machine-interface/d739db3d-b89f-46a4-ae02-97ac796261d0
        back_ref  floating-ip/958234f5-4fae-4afd-ae7c-d0dc3c608e06

    The resource path can contain selectors:

    .. code-block:: bash

        admin@localhost:/> relative logical-router/6f71ab62-d831-4a10-807c-975e23dcc3d8 service-instance/virtual-machine/virtual-machine-interface[virtual_machine_interface_properties.service_interface_type=right]/instance-ip
        instance-ip/ea329dca-e30e-42eb-93a3-86325a34a525
        admin@localhost:/> cat instance-ip/ea329dca-e30e-42eb-93a3-86325a34a525 | jq .instance_ip_address
        "172.24.4.3"

    This will get the SNAT public IP of a logical router.
    """
    description = "Get linked resources by providing a resource name path"
    path = Arg(help="Base resource", metavar='path',
               complete="resources::path")
    resource_name_path = Arg(help="Resource names separated by '%s'" % RESOURCE_NAME_PATH_SEPARATOR,
                             metavar='resource_name_path')
    show_intermediate = Option('-l',
                               default=False, action="store_true",
                               help="show intermediate resources")

    def _selector_to_python(self, selector):
        try:
            sel, value = selector.split('=')
        except:
            raise CommandError('Bad selector format %s\n'
                               'Selector must be of form "key1=value,key2.keyA=value"'
                               % selector)
        # guess if the value is an integer or boolean
        # otherwise fallback to string
        if value in ('false', 'true'):
            value = '%s' % value[0].upper() + value[1:]
        else:
            try:
                value = '%d' % value
            except TypeError:
                value = '"%s"' % value
        # key.key is transformed to ["key"]["key"]
        keys = sel.split('.')
        return "".join(['["%s"]' % k for k in keys]) + '==' + value

    def _select_next_resource(self, res_list, selectors):
        if len(res_list) == 0:
            return None
        # no selector, pick the first one for now
        if selectors is None:
            return res_list[0]
        # need to check all res against selectors
        try:
            res = res_list.pop(0)
            res.fetch()
        except IndexError:
            # end of res_list
            return None
        if not all([eval('res' + s) for s in selectors]):
            # res doesn't match selectors, continue
            return self._select_next_resource(res_list, selectors)
        # res matches, return
        return res

    def _get_next_resource(self, resource, next_resource_name, selectors):
        """
        :param resource: Resource (not necessary fetched)
        :param next_resource_name: string
        :rtype: (resource_type, resource_path)
        """
        # don't fetch twice
        if 'id_perms' not in resource:
            resource.fetch()

        res = None
        for res_list in (getattr(resource.refs, next_resource_name),
                         getattr(resource.back_refs, next_resource_name),
                         getattr(resource.children, next_resource_name)):
            res = self._select_next_resource(res_list, selectors)
            if res is not None:
                break

        if res is None:
            raise CommandError("Resource '%s' is not linked to resource type '%s'" %
                               (self.current_path(resource), next_resource_name))

        return (res.type, res)

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
        resource_name_paths_selectors = []
        for path in resource_name_paths:
            if '[' in path:
                matches = re.match('^([^[]*)\[([^]]+)\]$', path)
                if matches is not None:
                    selectors = [self._selector_to_python(s.strip())
                                 for s in matches.group(2).split(',')]
                    resource_name_paths_selectors.append((matches.group(1),
                                                          selectors))
                else:
                    raise CommandError('Bad path format: %s' % path)
            else:
                resource_name_paths_selectors.append((path, None))

        # Build resources along the path
        result = [(resource_type, resource)]
        for (resource_name, selectors) in resource_name_paths_selectors:
            resource_type, resource = self._get_next_resource(
                resource, resource_name, selectors)
            result.append((resource_type, resource))

        result = [(t, self.current_path(r)) for t, r in result]
        if show_intermediate:
            return format_table(result)
        else:
            return text_type(result[-1][1])
