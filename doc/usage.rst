Connecting to the API server
============================

Basic auth on localhost:8095
----------------------------

.. code-block:: bash

   $ contrail-api-cli --os-auth-plugin http \\
                      --os-username admin \\
                      --os-password paswword \\
                      --port 8095 \\
                      shell

.. code-block:: python

    from contrail_api_cli.client import SessionLoader
    from contrail_api_cli.resource import Collection
    from contrail_api_cli.context import Context
    from contrail_api_cli.schema import DummySchema

    session = SessionLoader().make(host="localhost",
                                   port=8095,
                                   os_username="admin",
                                   os_password="password",
                                   os_cacert=None,
                                   os_cert=None,
                                   insecure=False,
                                   timeout=1)

    Context().session = session
    Context().schema = DummySchema()

    print(len(Collection('virtual-network')))


Keystone auth on API_SERVER:8082
--------------------------------

.. code-block:: bash

   $ contrail-api-cli --os-auth-plugin v2password \\
                      --os-username admin \\
                      --os-password paswword \\
                      --os-tenant-name tenant_name \\
                      --os-auth-url https://keystone:5000/v2.0/ \\
                      shell

.. note::

   All parameters can be set in enviroment variables. For example,
   --os-auth-plugin looks for $OS_AUTH_PLUGIN.

   --port and --host correspond to $CONTRAIL_API_(HOST|PORT)

Base commands
=============

All commands provides a --help option.

help
----

List all available commands.

man
---

.. automodule:: contrail_api_cli.commands.man
    :members:
    :show-inheritance:

ls
--

.. automodule:: contrail_api_cli.commands.ls
    :members:
    :show-inheritance:

du
--

.. automodule:: contrail_api_cli.commands.du
    :members:
    :show-inheritance:

cd
--

.. autoclass:: contrail_api_cli.commands.shell.Cd
    :members:
    :show-inheritance:

cat
---

.. automodule:: contrail_api_cli.commands.cat
    :members:
    :show-inheritance:

tree
----

.. automodule:: contrail_api_cli.commands.tree
    :members:
    :show-inheritance:

rm
--

.. automodule:: contrail_api_cli.commands.rm
    :members:
    :show-inheritance:

edit
----

.. automodule:: contrail_api_cli.commands.edit
    :members:
    :show-inheritance:

schema
------

.. automodule:: contrail_api_cli.commands.schema
    :members:
    :show-inheritance:

ln
--

.. automodule:: contrail_api_cli.commands.ln
    :members:
    :show-inheritance:

relative
--------

.. automodule:: contrail_api_cli.commands.relative
    :members:
    :show-inheritance:

kv
--------

.. automodule:: contrail_api_cli.commands.kv
    :members:
    :show-inheritance:

Advanced usage
==============

pipes
-----

Any command can be piped to any program installed on the system inside the cli shell.

.. code-block:: bash

    admin@localhost:/virtual-network> cat 1095e416-b7cd-4c65-b0a3-631e8263a4dd | grep dns
    "dns_nameservers": [],
                "dns_server_address": "192.168.21.2",
    admin@localhost:/virtual-network> cat 1095e416-b7cd-4c65-b0a3-631e8263a4dd | jq '.network_ipam_refs[].attr.ipam_subnets[].dns_server_address'
    "192.168.21.2"

direct-call
-----------

You can call command directly from bash and pipe or redirect output as you wish.

.. code-block:: bash

    $ contrail-api-cli ls /virtual-network
    virtual-network/1095e416-b7cd-4c65-b0a3-631e8263a4dd
    virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413
    virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70
    virtual-network/e3148147-164e-4194-8507-a58eefe072bd
    virtual-network/ba2170ce-741c-4361-ad88-f2d97162faf2
    virtual-network/e82ae164-f78a-4766-8ba2-7cb68dacaecb

wildcard resolution
-------------------

The wildcards * and ? can be used in paths. All matching resources will be resolved.

.. warning:: Note that this does filtering on the cli side and not on the API side.

.. code-block:: bash

    admin@localhost:/> ls -l virtual-network/default-domain:admin:*
    virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413  default-domain:admin:net2
    virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1

loading commands from other namespaces
--------------------------------------

Say you have a collection of commands in the ``contrail_api_cli.mycommands``
entrypoint, run:

.. code-block:: bash

    $ contrail_api_cli --ns contrail_api_cli.mycommands shell

The namespace ``contrail_api_cli.mycommands`` commands will
be loaded as well as the commands of the default ``contrail_api_cli.command``
namespace.

python from the shell
---------------------

You can directly use contrail-api-cli API in a python console that can be
run with the ``python`` command. If ptpython [1]_ or IPython [2]_ are
installed they will be used instead of the standard python repl.

.. code-block:: python

    admin@localhost:/> python
    >>> c = Collection('virtual-network', fetch=True)

    >>> for vn in c:
    ...     print(vn.uuid)
    0287b4d1-3aea-4a82-b1be-be524995d1a8
    73fc0e08-b542-483e-86e7-f4a5aad2750f
    bf91b645-f7aa-4ab3-88cf-dc7a6358c08c
    a3694461-c4e0-4f54-a6fa-a11ae0472e04
    6afc9f77-607f-424c-8188-996c9513467a

python script execution
-----------------------

The `exec` command can be used to run a python script that is using the
contrail_api_cli API. This avoids the need to setup the connection to
the API server inside the script since the script will be run in the
context of the cli.

.. code-block:: bash

    $ contrail-api-cli exec my_script.py

.. [1] https://github.com/jonathanslenders/ptpython
.. [2] https://ipython.org/
