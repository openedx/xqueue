xqueue
======

RabbitMQ clustering notes (Source: http://www.rabbitmq.com/clustering.html)

0) Stop all rabbitmq servers
rabbitmqctl stop_app

1) Instances must be able to refer to each other by short names

Instance1:
/etc/hostname:
    rabbit1
/etc/hosts:
    10.96.127.153 rabbit1
    10.96.127.154 rabbit2

Instance2:
/etc/hostname:
    rabbit2
/etc/hosts:
    10.96.127.153 rabbit1
    10.96.127.154 rabbit2

2) Instances must share same string cookie at
    /var/lib/rabbitmq/.erlang.cookie

rabbitmqctl stop 
