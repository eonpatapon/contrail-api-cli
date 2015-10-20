[![Build Status](https://travis-ci.org/eonpatapon/contrail-api-cli.svg?branch=master)](https://travis-ci.org/eonpatapon/contrail-api-cli)
contrail-api-cli
================
Simple CLI program to browse Contrail API server

## Install first

You can install contrail-api-cli inside a python virtualenv. 
First create the virtualenv and install contrail-api-cli with pip.

    $ virtualenv contrail-api-cli-venv
    $ source contrail-api-cli-venv/bin/activate
    (contrail-api-cli-venv) $ pip install contrail-api-cli

## Now use it

On an Opencontrail/devstack, you can run the tool with

    (contrail-api-cli-venv) $ contrail-api-cli

## Now, what if

### virtualenv is missing
Install virtualenv

    # pip install virtualenv

### pip is missing
Install pip

    # easy_install pip
