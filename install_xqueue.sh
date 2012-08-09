#!/usr/bin/env bash

# The following sets up and runs a single-node Xqueue server
#----------------------------------------------------------------------

# Install requirements
apt-get update
apt-get install nginx gunicorn rabbitmq-server
apt-get install python-pip python-mysqldb
pip install django requests pika boto

# Set up nginx proxy, then restart
cp nginx.conf /etc/nginx/nginx.conf
/etc/init.d/nginx restart

# Start RabbitMQ
rabbitmqctl start_app

# Start gunicorn from ~/xserver/xqueue
gunicorn --workers=4 -b 127.0.0.1:3031 xqueue.wsgi &

# Optional: Start queue listeners
# queue/queue_consumer.py


