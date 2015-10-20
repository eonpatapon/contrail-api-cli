[![Build Status](https://travis-ci.org/eonpatapon/contrail-api-cli.svg?branch=master)](https://travis-ci.org/eonpatapon/contrail-api-cli)

contrail-api-cli
================
Simple CLI program to browse Contrail API server

## Installation

You can install contrail-api-cli inside a python virtualenv. 
First create the virtualenv and install contrail-api-cli with pip.

    $ virtualenv contrail-api-cli-venv
    $ source contrail-api-cli-venv/bin/activate
    (contrail-api-cli-venv) $ pip install contrail-api-cli

## Usage

Run ``contrail-api-cli`` to start the cli. Use the ``-h`` option to see all supported options. By default it will try to connect to ``localhost`` on port ``8082`` with no authentication.
    
Type ``help`` to get the list of all available commands.

Here is a screenshot of an example session:

![Example session](http://i.imgur.com/X83FVTJ.png)

## What if

### virtualenv is missing

Install virtualenv

    # pip install virtualenv

### pip is missing

Install pip

    # easy_install pip
