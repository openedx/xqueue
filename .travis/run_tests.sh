#!/bin/bash -xe
. /edx/app/xqueue/venvs/xqueue/bin/activate

cd /edx/app/xqueue/xqueue

tox
