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

ls
--

List resources and collections.

.. code-block:: bash

    # list API collections
    admin@localhost:/> ls
    domain
    global-vrouter-config
    instance-ip
    network-policy
    virtual-DNS-record
    route-target
    loadbalancer-listener
    floating-ip
    floating-ip-pool
    physical-router
    [...]

    # list collection
    admin@localhost:/> ls global-system-config
    global-system-config/d6820999-c8fe-45ae-acb2-48aebddb3b7d

    # long format
    admin@localhost:/> ls -l virtual-network
    virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413  default-domain:admin:net2
    virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
    virtual-network/e3148147-164e-4194-8507-a58eefe072bd  default-domain:default-project:default-virtual-network
    virtual-network/ba2170ce-741c-4361-ad88-f2d97162faf2  default-domain:default-project:ip-fabric
    virtual-network/e82ae164-f78a-4766-8ba2-7cb68dacaecb  default-domain:default-project:__link_local__

    # parametrized output format
    admin@localhost:/> ls -l -c instance_ip_address instance-ip
    instance-ip/f9d25887-2765-4ba0-bf45-54b9dbc5874a  192.168.20.1
    instance-ip/deb82100-00bb-4b5c-8495-4bbe34b5fab8  192.168.21.1
    instance-ip/2f5c047d-0a9c-4709-bcfa-d710ac68cc22  192.168.10.3
    instance-ip/04cb356a-fb1f-44fa-bb2f-d0f0dd4eedfd  192.168.20.3

    # filter by parent_uuid
    admin@localhost:/> ls -l -p d0afbb0b-dd83-4a33-a673-9cb2b244e804 virtual-network
    virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
    virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413  default-domain:admin:net2

    # filter by attribute
    admin@localhost:/> ls -l -f instance_ip_address=192.168.20.1 instance-ip
    instance-ip/f9d25887-2765-4ba0-bf45-54b9dbc5874a  f9d25887-2765-4ba0-bf45-54b9dbc5874a


count
-----

Count resources of a collection.

.. code-block:: bash

    admin@localhost:/> count virtual-network
    6

cd
--

Change current context.

.. code-block:: bash

    admin@localhost:/> cd virtual-network
    admin@localhost:/virtual-network> ls
    1095e416-b7cd-4c65-b0a3-631e8263a4dd
    49d00de8-4351-446f-b6ee-d16dec3de413
    [...]
    admin@localhost:/virtual-network> ls instance-ip
    No resource found
    admin@localhost:/virtual-network> ls /instance-ip
    /instance-ip/f9d25887-2765-4ba0-bf45-54b9dbc5874a
    /instance-ip/deb82100-00bb-4b5c-8495-4bbe34b5fab8
    /instance-ip/2f5c047d-0a9c-4709-bcfa-d710ac68cc22
    /instance-ip/04cb356a-fb1f-44fa-bb2f-d0f0dd4eedfd

cat
---

Print resource details in json format.

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

tree
----

Show tree of references of a resource.

.. code-block:: bash

    # tree of references
    admin@localhost:/> tree logical-router/dd954810-d614-4892-9ec6-9a9595cc64ff
    /logical-router/dd954810-d614-4892-9ec6-9a9595cc64ff                 default-domain:admin:router1
    ├── /virtual-machine-interface/18b02f01-4300-427f-a646-0a44351034a6  default-domain:admin:18b02f01-4300-427f-a646-0a44351034a6
    │   ├── /routing-instance/2f6907e9-20e7-415a-9969-bb5af375574d       default-domain:admin:net2:net2
    │   │   ├── /route-target/721618d4-0861-4bda-8a33-bb116584d4bb       target:64512:8000005
    │   │   ├── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053       target:64512:8000003
    │   │   └── /route-target/ecd725e8-6523-428b-9811-00828926f91b       target:64512:8000002
    │   ├── /virtual-network/49d00de8-4351-446f-b6ee-d16dec3de413        default-domain:admin:net2
    │   │   └── /network-ipam/0edc36a1-c802-47be-b230-4b462d905b93       default-domain:default-project:default-network-ipam
    │   └── /security-group/8282a986-b9fd-4be1-96bd-ab100bd2bb8e         default-domain:admin:default
    ├── /virtual-machine-interface/6d9637e5-99ae-4d09-950e-50353b29411c  default-domain:admin:6d9637e5-99ae-4d09-950e-50353b29411c
    │   ├── /routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55       default-domain:admin:net1:net1
    │   │   ├── /route-target/79b5278c-a846-49f4-82ab-f1b8c05aff67       target:64512:8000001
    │   │   └── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053       target:64512:8000003
    │   ├── /virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70        default-domain:admin:net1
    │   │   └── /network-ipam/0edc36a1-c802-47be-b230-4b462d905b93       default-domain:default-project:default-network-ipam
    │   └── /security-group/8282a986-b9fd-4be1-96bd-ab100bd2bb8e         default-domain:admin:default
    └── /route-target/d0e33aea-f63d-403b-a3e7-5bcef88e6053               target:64512:8000003

    # tree of parents
    admin@localhost:/> tree -p routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55
    /routing-instance/5692de00-533a-4911-965b-dd9f6dbc6f55     default-domain:admin:net1:net1
    └── /virtual-network/5a9fbd42-a730-42f7-9947-be8a5d808b70  default-domain:admin:net1
        └── /project/d0afbb0b-dd83-4a33-a673-9cb2b244e804      default-domain:admin
            └── /domain/cbc6051f-fd47-4a26-82ee-cb3482926e17   default-domain

rm
--

Delete a resource from the API.

edit
----

Edit the json representation of a resource in an editor. Modification are sent
to the API server.

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
