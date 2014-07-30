# Instructions for configuring xqueue for local development.

Need a user and password for the lms to log in as.

There's a management command, which is a bit funny since it's intended for AWS.

Create a file named `auth.json` in the base xqueue directory with the below contents:

```{"USERS": {"lms": "abcd"}}```
    
Run

`django-admin.py update_users --pythonpath=. --settings=xqueue.settings`

In `settings.py`, add the queues you want to use to the `XQUEUES` dictionary.  Value should be `None` if your consumer will be pulling from the queue, or the url the queue should call to process each element.  (If you're using `xserver` point it at that, e.g. `'http://127.0.0.1:3031'` if you're running xserver on port 3031.

Running the service:

`django-admin.py runserver 127.0.0.1:3032 --pythonpath=. --settings=xqueue.settings`

The LMS config in edx-platform/lms/envs/dev.py needs to point to the queue: put the right url (`'http://127.0.0.1:3032'`) and password (`'abcd'`) in the `XQUEUE_INTERFACE` dict.

It will look like this:

XQUEUE_INTERFACE = {
    "url": 'http://127.0.0.1:3031',
    "django_auth": {
        "username": "lms",
        "password": "abcd"
    },
    "basic_auth": ('anant', 'agarwal'),
}
