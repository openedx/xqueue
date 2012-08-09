#!/usr/bin/env bash

# The following sets up and runs a single-node Xqueue server
#----------------------------------------------------------------------

# 1) Install requirements
apt-get update
apt-get install nginx gunicorn rabbitmq-server
apt-get install python-pip python-mysqldb
pip install django requests pip pika

# 2) Need xqueue files
# apt-get install git
# cd ~
# git clone https://github.com/MITx/xserver.git

# 3) Set up nginx conf (nginx.conf attached)

# 4) Start services
# rabbitmqctl start_app
# /etc/init.d/nginx restart

# 5) Start gunicorn from ~/xserver/xqueue
# gunicorn --workers=4 -b 127.0.0.1:3031 xqueue.wsgi

# 6) Optional: Start queue listeners
# ~/xserver/xqueue/queue/queue_consumer.py


