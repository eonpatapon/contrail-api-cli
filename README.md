[![Build Status](https://travis-ci.org/eonpatapon/contrail-api-cli.svg?branch=master)](https://travis-ci.org/eonpatapon/contrail-api-cli)
contrail-api-cli
================
Simple CLI program to browse Contrail API server

## Install first
You can install contrail-api-cli inside a python virtualenv. First create the virtualenv and install the app

    # virtualenv contrail-api-cli-venv
    # source contrail-api-cli-venv/bin/activate
    (contrail-api-cli-venv) # cd contrail-api-cli
    (contrail-api-cli-venv) # python setup.py install

## Now use it
On an Opencontrail / devstack, you can run the tool with

    (contrail-api-cli-venv) # contrail-api-cli --host 127.0.0.1:8082

## Now, what if
### virtualenv is missing
Install virtualenv

    # pip install virtualenv


### pip is missing
Install pip

    # easy_install pip


