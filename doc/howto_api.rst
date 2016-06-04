Using Resource and Collection API in commands
=============================================

``contrail-api-cli`` provides a minimal API to make common REST operations
(GET/PUT/POST/DELETE) on API resources.

To illustrate the usage of this API we will write a command to provision
vrouters in the API. Contrail already provides a provisioning script for
that but it is a good example for playing with contrail-api-cli API.

In this tutorial we will create three commands. Of course we would like to
provision new vrouters but we also would like to list them easily and to
delete them if needed.

Resource and Collection objects
-------------------------------

:class:`Resource` and :class:`Collection` objects are available in the
``contrail_api_cli.resource`` module. A collection represents
a list of resources in the API server. :class:`Collection` is an
iterable and :class:`Resource` is a dict that can seemlessly be
converted to the JSON representation of the resource.

For more details check the :ref:`api` page.

virtual-router resource
-----------------------

``contrail-api-cli`` API is a thin wrapper around the JSON representation of
resources or collections. Therefore we have to know a little about the
resource we would like to create. With the CLI we can inspect an existing
virtual router to see what the JSON representation look like::

    $ contrail-api-cli shell
    admin@localhost /> ls virtual-router
    virtual-router/7c5d76a8-7ca3-43a6-bee6-154f84db977e
    virtual-router/37fc1054-0d25-4a2d-aa42-9e202b5dfa3a
    admin@localhost /> cat virtual-router/37fc1054-0d25-4a2d-aa42-9e202b5dfa3a
    {
      "display_name": "node-2",
      "fq_name": [
        "default-global-system-config",
        "node-2"
      ],
      "href": "http://localhost:8082/virtual-router/37fc1054-0d25-4a2d-aa42-9e202b5dfa3a",
      "id_perms": {
        [...]
      },
      "name": "node-2",
      "parent_href": "http://localhost:8082/global-system-config/69e8ab08-f1d3-474d-8c7f-c540410fa025",
      "parent_type": "global-system-config",
      "parent_uuid": "69e8ab08-f1d3-474d-8c7f-c540410fa025",
      "uuid": "37fc1054-0d25-4a2d-aa42-9e202b5dfa3a",
      "virtual_machine_refs": [
        [...]
      ],
      "virtual_router_ip_address": "10.11.0.56"
    }


So some useful information would be the ``virtual_router_ip_address``
property. The virtual router hostname can be found in the ``fq_name``.

List command
------------

The list command make use of the :class:`Collection` object which represent the
collection of resources of a specific type.

Basically doing ``ls /`` in the CLI gives you all collections::

    from contrail_api_cli.command import Command
    from contrail_api_cli.resource import Collection
    from contrail_api_cli.utils import printo

    class ListVRouter(Command):
        description = 'List vrouters'

        def __call__(self):
            vrouters = Collection('virtual-router', fetch=True)
            for vrouter in vrouters:
                vrouter.fetch()
                printo('%s: %s', (vrouter.fq_name[-1],
                                  vrouter['virtual_router_ip_address']))

We instanciate a :class:`Collection` of type 'virtual-router' to get all the
vrouters from the API. The ``fetch`` argument will actually fetch the collection
data from the API server immediately. The method :func:`Collection.fetch` can
be used to sync the object later with the server.

The :class:`Collection` object is iterable like a list so we iterate the
collection and fetch the details of each resource to get the details. For
each vrouter we print the name and the IP of the vrouter. :class:`Resource`
is basically a dict wrapper so its properties are accessible directly.

:func:`printo` is used instead of :func:`print` to handle properly terminal
encoding with python2 and python3.

.. note::

    With Contrail >= 3.0 we can make use of the fields API on :class:`Collection`
    objects. Instead of making a GET request for each resource to get its details
    we can specify the supplementary fields to get in the :class:`Collection`::

        vrouter = Collection('virtual-router',
                             fields=['virtual_router_ip_address'],
                             fetch=True)
        for vrouter in vrouters:
            printo(vrouter['virtual_router_ip_address'])

    In this case only one GET request is made.


Add command
-----------

To add a virtual-router we need at least a name and an IP address.
The type is optionnal and is usually not defined but we add an option
for it just in case::

    from contrail_api_cli.command import Command, Arg, Option
    from contrail_api_cli.resource import Resource

    class AddVRouter(Command):
        description = 'Add vrouter'
        vrouter_name = Arg(help='Hostname of compute node')
        vrouter_ip = Option(help='IP of compute node',
                            required=True)
        vrouter_type = Option(help='vrouter type',
                              choices=['tor-service-mode', 'embedded'],
                              default=None)

        def __call__(self, vrouter_ip=None, vrouter_name=None, vrouter_type=None):
            global_config = Resource('global-system-config',
                                     fq_name='default-global-system-config')
            vrouter = Resource('virtual-router',
                               fq_name='default-global-system-config:%s' % vrouter_name,
                               parent=global_config,
                               virtual_router_ip_address=vrouter_ip)
            if vrouter_type:
                vrouter['virtual_router_type'] = [vrouter_type]
            vrouter.save()

To create the vrouter resource we are making use of the :class:`Resource` class. To
create a :class:`Resource` we need to pass the type ('virtual-router'), an fq_name,
and a parent resource.

.. note::

    :class:`Resource` is a subclass of python :class:`UserDict`. Any supplementary
    kwarg passed to the constructor is added in the dict. In our example
    passing ``virtual_router_ip_address`` to the constructor is the same as::

        vrouter = Resource('virtual-router',
                           fq_name='default-global-system-config:%s' % vrouter_name,
                           parent=global_config)
        vouter['virtual_router_ip_address'] = vrouter_ip

An existing parent resource must be defined in order to create the resource. In
our case the parent is the 'default-global-system-config'. Passing a parent
resource will populate the `parent_type` and `parent_uuid` keys of the :class:`Resource`.

Finally we save the resource to the API server using the :func:`Resource.save` method. This
method convert the object to JSON and send the data to the API server in a POST request
since the resource doesn't exists on the server. It is possible to update an existing
resource using the same method. In the update case a PUT request is made.

Del command
-----------

The del command is straith forward. We need to get the resource by it's name
and try to delete it with the :func:`Resource.delete` method::

    class DelVRouter(Command):
        description = 'Remove vrouter'
        vrouter_name = Arg(help='Hostname of compute node')

        def __call__(self, vrouter_name=None):
            vrouter = Resource('virtual-router',
                               fq_name='default-global-system-config:%s' % vrouter_name,
                               check=True)
            vrouter.delete()

The ``check`` param makes sure that the resource exists on the API server. If not
:class:`ResourceNotFound` is raised and catched automatically by the cli.

.. note::

    :func:`Resource.check` only validate the ``fq_name`` of the resource
    whereas :func:`Resource.fetch` will try to get all the details of
    the resource. Both methods can raise :class:`ResourceNotFound`. Using
    ``check=True`` or ``fetch=True`` when initializing a :class:`Collection`
    is the same as using theses methods.
