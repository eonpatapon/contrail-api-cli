Howto write a command
=====================

The code presented here is available at https://github.com/eonpatapon/contrail-api-cli-howto.

Setup your project
------------------

First thing is to create a standard python project with a ``setup.py`` file.
The structure would look like::

    contrail-api-cli-howto/
    ├── howto
    │   └── __init__.py
    └── setup.py

Our ``setup.py`` can be as simple as::

    from setuptools import setup, find_packages

    setup(
        name='contrail-api-cli-howto',
        version='0.1',
        packages=find_packages(),
        install_requires=[
            'contrail-api-cli'
        ]
    )

Hello world command
-------------------

In ``howto/__init__.py`` we define our command::

    from __future__ import unicode_literals

    from contrail_api_cli.command import Command


    class Hello(Command):
        description = 'Hello world command'

        def __call__(self):
            return 'Hello world !'

Any command must inherit from the Command class. The final output of the
command should be returned by the ``__call__`` method. The output needs to be
unicode so that the terminal encoding is handled properly.

Register the command in the cli
+++++++++++++++++++++++++++++++

As our command is in its own package it won't be available in the cli yet.
We don't even know what is the command name.

The cli discover available commands using python entrypoints. By default the
cli loads commands from the ``contrail_api_cli.command`` entrypoint. To register
our command our ``setup.py`` becomes::

    from setuptools import setup, find_packages

    setup(
        name='contrail-api-cli-howto',
        version='0.1',
        packages=find_packages(),
        install_requires=[
            'contrail-api-cli'
        ],
        entry_points={
            'contrail_api_cli.command': [
                'hello = howto:Hello'
            ]
        }
    )

The command name will be ``hello`` in the cli. We need to install our packages so that
the entrypoint is registered in the python path

.. code-block:: bash

    $ python setup.py develop
    $ contrail-api-cli hello -h
    usage: contrail-api-cli hello [-h]

    optional arguments:
      -h, --help  show this help message and exit
    $ contrail-api-cli hello
    Hello World !

Adding command arguments
++++++++++++++++++++++++

Commands can take options and arguments. The standard argparse lib is used to declare
and parse command parameters.

We will include an option in our command to greet someone::

    from __future__ import unicode_literals

    from contrail_api_cli.command import Command, Arg


    class Hello(Command):
        description = 'Hello world command'
        who = Arg(nargs='?', default='cli', help='Person to greet')

        def __call__(self, who=None):
            return 'Hello world %s !' % who

The options are added as class attributes using the ``Arg`` class which can take the same
arguments as ``argparse.ArgumentParser.add_argument``. The only difference is that if you
don't specicy the option name, the attribute name will be used instead. In our case the argument
name will be ``who``. All arguments are passed to the ``__call__`` method as keyword arguments.

We can see the result using the ``-h`` option.

.. code-block:: bash

    $ contrail-api-cli hello -h
    usage: contrail-api-cli hello [-h] [who]

    positional arguments:
      who         Person to greet

    optional arguments:
      -h, --help  show this help message and exit

    $ contrail-api-cli hello
    Hello world cli !
    $ contrail-api-cli hello foo
    Hello world foo !
