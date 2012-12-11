import pika
from django.conf import settings


def push_to_queue(queue_name, qitem=None):
    '''
    Publishes qitem (serialized data) to a specified queue.
    Returns the number of outstanding messages in specified queue
    '''
    queue_name = str(queue_name)  # Important: queue_name cannot be unicode!

    if queue_name == 'null':
        return 0
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER,
                                            settings.RABBITMQ_PASS)
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        credentials=credentials, host=settings.RABBIT_HOST))
    channel = connection.channel()
    q = channel.queue_declare(queue=queue_name, durable=True)
    if qitem is not None:
        channel.basic_publish(exchange='',
            routing_key=queue_name,
            body=qitem,
            properties=pika.BasicProperties(delivery_mode=2),
            )
    connection.close()
    return q.method.message_count


def get_queue_length(queue_name):
    """
    push_to_queue is not a great name for a function
    that returns the queue length, so make an alias
    """
    return push_to_queue(queue_name)
