[![Build Status](https://travis-ci.org/eonpatapon/contrail-api-cli.svg?branch=master)](https://travis-ci.org/eonpatapon/contrail-api-cli)
[![Doc Status](https://readthedocs.org/projects/contrail-api-cli/badge/?version=latest)](http://contrail-api-cli.readthedocs.org/en/latest/)
[![Coverage Status](https://coveralls.io/repos/github/eonpatapon/contrail-api-cli/badge.svg?branch=master)](https://coveralls.io/github/eonpatapon/contrail-api-cli?branch=master)
[![Join the chat at https://gitter.im/eonpatapon/contrail-api-cli](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/eonpatapon/contrail-api-cli?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

contrail-api-cli
================
Simple CLI program to browse Contrail API server

## Installation

### Python virtualenv

You can install contrail-api-cli inside a python virtualenv. 
First create the virtualenv and install contrail-api-cli with pip.

    $ virtualenv contrail-api-cli-venv
    $ source contrail-api-cli-venv/bin/activate
    (contrail-api-cli-venv) $ pip install contrail-api-cli

### Debian package

First you need to satisfy dependencies missing in Ubuntu Trusty. You can
install them from newer distribution or from backports (eg.
[tcpcloud/extra](https://launchpad.net/~tcpcloud/+archive/ubuntu/extra))

- python-pathlib
- python-prompt-toolkit
- python-wcwidth

When dependencies are satisfied, you can build package:

    dpkg-buildpackage -uc -us

Then upload into your repository or install directly:

    dpkg -i ../contrail-api-cli_*.deb

## Usage

Run ``contrail-api-cli shell`` to start the cli. Use the ``-h`` option to see all supported options. By default it will try to connect to ``localhost`` on port ``8082`` with no authentication.
    
Type ``help`` to get the list of all available commands.

Here is a screenshot of an example session:

![Example session](http://i.imgur.com/X83FVTJ.png)

## Authentication

``contrail-api-cli`` supports keystone (v2, v3) and Basic HTTP authentication mechanisms.

When running the contrail API server with ``--auth keystone`` you can login on port 8082 with keystone auth and on port 8095 with basic http auth.

### Basic HTTP auth

    contrail-api-cli --host localhost:8095 --os-auth-plugin http --os-username admin --os-password contrail123 shell

The username and password can be sourced from the environment variables ``OS_USERNAME``, ``OS_PASSWORD``.

The auth plugin default to ``http`` unless ``OS_AUTH_PLUGIN`` is set.

### Kerberos auth

The easiest way is to source your openstack openrc file and run

    contrail-api-cli --os-auth-plugin [v2password|v3password] shell

See ``contrail-api-cli --os-auth-plugin [v2password|v3password] --help`` for all options.

## What if

### virtualenv is missing

Install virtualenv

    # pip install virtualenv

### pip is missing

Install pip

    # easy_install pip
