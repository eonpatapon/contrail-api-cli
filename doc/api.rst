.. _api:

API
===

Collection
----------

.. autoclass:: contrail_api_cli.resource.Collection
    :members:
    :inherited-members: path, href

Resource
--------

.. autoclass:: contrail_api_cli.resource.Resource
    :members:
    :inherited-members: path, href

Command
-------

.. autoclass:: contrail_api_cli.command.Command
    :members:
    :special-members: __call__
    :inherited-members: description

Utils
-----

.. autofunction:: contrail_api_cli.utils.format_table
.. autofunction:: contrail_api_cli.utils.format_tree
.. autofunction:: contrail_api_cli.utils.continue_prompt
.. autofunction:: contrail_api_cli.utils.md5
.. autofunction:: contrail_api_cli.utils.parallel_map
