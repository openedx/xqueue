#!/usr/bin/env bash

# The following sets up and runs a single-node Xqueue server
#----------------------------------------------------------------------

# Install requirements
apt-get update
apt-get install nginx gunicorn rabbitmq-server
apt-get install python-pip python-mysqldb
pip install -R pre-requirements.txt
pip install -R requirements.txt

# Set up nginx proxy, then restart
cp nginx.conf /etc/nginx/nginx.conf
/etc/init.d/nginx restart
mkdir ../log

# Start RabbitMQ
rabbitmqctl start_app

# Create DB
python manage.py syncdb

# Start gunicorn from ~/xserver/xqueue
./run.sh

# Optional: Start queue listeners
# python manage.py consumer 4
