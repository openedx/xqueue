**NOTE**: This document describes the in-progress "v2" of the checker API, not the existing approach implemented by xqueue, etc.

External Checkers API
=====================


Overview
========

The Checkers API allows third party applications (**checkers**) to consume
student **submissions** for specific problem **types** from a named **queue**.
The checker is in charge of processing the submission and publish a
**result**. The applications acquire a *lease* when they start working on
the submission, allowing the queue to track which application is
handling each submission and for how long.

The API is designed to be used over HTTP, using the REST style.
Checkers poll a queue to check if there are new submissions and leasing
them if appropriate. Checkers can also subscribe a HTTP URL which will
be notified when new submissions are available in a queue.


Queue Naming
------------

The name of the queue where the submission will go is defined in the
problem at the LMS level. The default queue name follows the following
structure: ``{course-id}/{problem-type}``. The name of the queue can be
overwritten by the content author, for example to specify a particular
problem: ``{course-id}/problem-2``.


Walk-through
------------


Basic Usage Example
~~~~~~~~~~~~~~~~~~~


1. (Optional) Retrieve the state of the Queue doing a GET on the Queue URL.

::

    Request:
    GET /checker/v1/queue/{queue-name} HTTP/1.1
    Host: api.edx.org
    ...
    
    
    Response:
    HTTP/1.1 200 OK
    ...
    Content-Type: application/json
    Content-Length: {length}
    
    {
        "name": "queue-name",
        "url": "https://{host}/{path}/queue/{queue-name}",
        "length": {queue-length}
    }


2. If there are submissions available, lease one from the Queue.

::

    Request:
    POST /checker/v1/queue/{queue-name}/lease HTTP/1.1
    Host: api.edx.org
    ...
    
    Response:
    HTTP/1.1 201 Created
    ...
    Content-Type: application/json
    Content-Length: {length}
    
    {
        "submissions": [
            {
                "id": "{submission-id}",
                "type": "{problem-type}",
                "url": "https://api.edx.org/checker/v1/submission/{submission-id}",
                "state": "LEASED",
                "enqueue": 1368459052,
                "expires": 1368459112,
                "payload": {student-submission}
            }
        ]
    }


3. Process the submission payload according to the problem type and
   publish the result.

::

    Request:
    PATCH /checker/v1/submission/{submission-id} HTTP/1.1
    Host: api.edx.org
    ...
    
    {
        "state": "SUCCESS",
        "result": {checker-response} 
    }
    
    
    Response:
    HTTP/1.1 204 No Content
    ...





Notifications Example
~~~~~~~~~~~~~~~~~~~~~

To avoid constant polling, it is possible for an application to
subscribe to a Queue by registering an endpoint that will be called
when there are submissions pending in the Queue.


1. Register URL for notifications

::

    Request:
    POST /checker/v1/queue/{queue-name}/subscription HTTP/1.1
    Host: api.edx.org
    ...
     
    {
        "endpoint": "http://{endpoint-host}/{endpoint-path}",
    }
    
    Response:
    HTTP/1.1 201 Created
    Location: https://api.edx.org/checker/v1/queue/{queue-name}/subscription/{subscription-id}
    ...
    {
      "id": "{subscription-id}",
      "url": "{subscription-url}",
      "queue-name": "{queue-name}",
      "queue-url": "{queue-url}",
      "endpoint": "http://{endpoint-host}/{endpoint-path}"
    }


2. A ``POST`` request with a Queue resource will be done to the
   specified endpoint. The response code should be ``202 Accepted``.

::

    Request:
    POST /{endpoint-path} HTTP/1.1
    Host: {endpoint-host}
    Content-Type: application/json
    Content-Length: {length}
    ...
    
    {
        "name": "{queue-name}",
        "url": "https://api.edx.org/checker/v1/{path}/{queue-name}",
        "length": {queue-length}
    }
    
    Response:
    HTTP/1.1 202 Accepted
    ...


API Specification
=================


Common Elements
---------------


Transport Protocol
~~~~~~~~~~~~~~~~~~

The API is designed to be used over HTTP 1.1 (`RFC 2616`_).


Authentication and Encryption
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**TBD** Each request will be authenticated using Basic Authentication
(`RFC 2617`_).

Request send over the public Internet should use the HTTPS protocol
(`RFC 2818`_).


Media Types
~~~~~~~~~~~

All resource representations and requests must be encoded in JSON
(`RFC 4627`_). The preferred content type for all representations and
requests is ``application/vnd.edx.xqueue+json``. The standard content
type for JSON, ``application/json``, should be also acceptable.


Request Headers
~~~~~~~~~~~~~~~

+--------------------+---------------------------------------------------+----------------------------------------------------+
| Header             | Description                                       | Required                                           |
+====================+===================================================+====================================================+
| ``Content-Length`` | Length in bytes of the request body.              | Yes on requests that contain a message body.       |
+--------------------+---------------------------------------------------+----------------------------------------------------+
| ``Content-Type``   | Media type describing the request message body.   | Yes on requests that contain a message body.       |
+--------------------+---------------------------------------------------+----------------------------------------------------+
| ``Host``           | Identifies the origin host receiving the message. | Yes, on all requests. Required to Virtual Hosting. |
+--------------------+---------------------------------------------------+----------------------------------------------------+


Request Methods
~~~~~~~~~~~~~~~

The External Checkers API uses the following standard HTTP methods:

+------------+------------------------------+
| Method     | Description                  |
+============+==============================+
| ``GET``    | Retrieve representation.     |
+------------+------------------------------+
| ``POST``   | Create a new resource.       |
+------------+------------------------------+
| ``PUT``    | Update a resource.           |
+------------+------------------------------+
| ``PATCH``  | Partially update a resource. |
+------------+------------------------------+
| ``DELETE`` | Delete a resource.           |
+------------+------------------------------+


Request Parameters
~~~~~~~~~~~~~~~~~~

For ``GET`` requests, the parameters are passed in the URL, using the
query section if necessary.

For ``POST``, ``PUT`` or ``PATCH`` requests, the parameters that are not
part of the base URL are passed in the request body, JSON encoded and
with the appropriate ``Content-Type`` header.


Response Headers
~~~~~~~~~~~~~~~~

+--------------------+-------------------------------------------------------------------------------------------------+------------------------------------------------------------------+
| Header             | Description                                                                                     | Required                                                         |
+====================+=================================================================================================+==================================================================+
| ``Content-Length`` | Length in bytes of the request body.                                                            | Yes on requests that contain a message body.                     |
+--------------------+-------------------------------------------------------------------------------------------------+------------------------------------------------------------------+
| ``Content-Type``   | Media type describing the request message body.                                                 | Yes on requests that contain a message body.                     |
+--------------------+-------------------------------------------------------------------------------------------------+------------------------------------------------------------------+
| ``Location``       | Canonical URI for newly created resources.                                                      | Yes on reponses to request that create new resources.            |
+--------------------+-------------------------------------------------------------------------------------------------+------------------------------------------------------------------+
| ``Rety-After``     | Can be used with a 503 response to indicate how long the service is expected to be unavailable. | Yes on  503 responses to indicate that the server is overloaded. |
+--------------------+-------------------------------------------------------------------------------------------------+------------------------------------------------------------------+


Response Codes
~~~~~~~~~~~~~~

+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| HTTP Status                 | Description                                                                                                           |
+=============================+=======================================================================================================================+
| ``200 OK``                  | The request has succeeded. The information returned with the response is dependent on the method used in the request. |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``201 Created``             | The request has been fulfilled and resulted in a new resource being created.                                          | 
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``202 Accepted``            | The request has been accepted for processing, but the processing has not been completed.                              |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``204 No Content``          | The server has fulfilled the request but does not need to return a body.                                              |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``400 Bad Request``         | The request is malformed or is missing required fields.                                                               |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``409 Conflict``            | The request could not be completed due to a conflict with the current state of the resource.                          |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+
| ``503 Service Unavailable`` | The server is unable to handle the request due overload or maintenance.                                               |
+-----------------------------+-----------------------------------------------------------------------------------------------------------------------+


Errors
~~~~~~

In the event of an error, the appropriate status code will be returned
with a body containing more information.


API Reference
=============

For all the URL paths below assume a host (e.g. ``http://api.edx.org``)
and prefix path (e.g. ``/checker/v1/``).

For example:

``GET /submission/{id} HTTP/1.1``

should be interpreted as:

``GET /checker/v1/submission/{id} HTTP/1.1``



Queue
-----

A resource that represents a queue created to contain the submissions
from students to a particular problem or problem type. The queues are
created automatically when they are defined in the course content. The
state of the queue can be checked at any time.


Representation
~~~~~~~~~~~~~~

::

    {
        name: <String>,
        url: <String>,
        length: <Number>
    }

+------------+--------+----------------------------------------------+--------+----------+
| Property   | Type   | Description                                  | Access | Optional |
+============+========+==============================================+========+==========+
| ``name``   | String | Name of the Queue                            | Read   | No       |
+------------+--------+----------------------------------------------+--------+----------+
| ``url``    | String | URL for the Queue                            | Read   | No       |
+------------+--------+----------------------------------------------+--------+----------+
| ``length`` | Number | Number of submissions available on the Queue | Read   | No       |
+------------+--------+----------------------------------------------+--------+----------+


Methods
~~~~~~~

+-----------+------------------------------+-----------------------------------------------+
| Actions   | HTTP Request                 | Description                                   |
+===========+==============================+===============================================+
| ``get``   | ``GET /queue/{name}``        | Get Information about a Queue.                | 
+-----------+------------------------------+-----------------------------------------------+
| ``lease`` | ``POST /queue/{name}/lease`` | Lease one or more submissions from the Queue. |
+-----------+------------------------------+-----------------------------------------------+


``get`` method
``````````````

The get method is use to retrieve the status of a queue, listing the
number of submissions available to lease by the checker application.


parameters
++++++++++

+----------------+---------+--------------------+----------+
| Parameter      | Type    | Description        | Required |
+================+=========+====================+==========+
| ``name``       | String  | Name of the Queue. | Yes      |
+----------------+---------+--------------------+----------+


response
++++++++

If successful, the method returns a Queue representation in the
response body.


``lease`` method
````````````````

The lease method is used to lease one or many submissions for
processing. The checker application can optionally specify the lease
time and the number of submissions to lease. The response is a list of
leased submissions, which can be equal or less than the number of
leases requested.


parameters
++++++++++

+-------------+--------+-----------------------------------+----------+-------------------+
| Parameter   | Type   | Description                       | Required | Default           |
+=============+========+===================================+==========+===================+
| ``name``    | String | Name of the Queue.                | Yes      |                   |
+-------------+--------+-----------------------------------+----------+-------------------+
| ``seconds`` | Number | Duration of the Lease in seconds. | No       | *Queue dependent* |
+-------------+--------+-----------------------------------+----------+-------------------+
| ``count``   | Number | Number of Submissions to Lease.   | No       | 1                 |
+-------------+--------+-----------------------------------+----------+-------------------+


response
++++++++

If successful, the method returns in the response body a JSON object
with a single key named ``submissions``. The value of the key is a list
of Submission representations.

Returns code ``204 No Content`` if there are no submissions available.


Submission
----------

A resource representing a single submission or attempt from a student
to answer a problem. Initially, the submission contains a payload with
the student data. After being evaluated by the checker, the submission
is updated to include the result of the evaluation.

The structure of the payload and the result are determined by the
problem type. Each problem type should define how the payload should
be decoded and interpreted, and how the result should be formatted.


Representation
~~~~~~~~~~~~~~

::

    {
        id: <String>
        type: <String>
        url: <String>
        state: <String>
        enqueued: <Number>
        expires: <Number>
        payload: type-specific
        result:  type-specific
    }

+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| Property     | Type     | Description                                                             | Access     | Optional |
+==============+==========+=========================================================================+============+==========+
| ``id``       | String   | Unique identifier for the Submission.                                   | Read       | No       | 
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``type``     | String   | The Problem Type. Case insensitive.                                     | Read       | No       |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``url``      | String   | URL for the Submission.                                                 | Read       | No       |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``state``    | String   | ``PENDING`` \| ``LEASED`` \| ``SUCCESS`` \| ``ERROR`` \| ``EXPIRED``    | Read-Write | No       |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``enqueued`` | Number   | Unix Time Timestamp when the submission was queued.                     | Read       | No       |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``expires``  | Number   | Unix Time Timestamp when the lease will expire.                         | Read-Write | Yes      |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``payload``  | Variable | Dependend on the problem type.                                          | Read       | No       |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+
| ``result``   | Variable | Dependend on the problem type.                                          | Read-Write | Yes      |
+--------------+----------+-------------------------------------------------------------------------+------------+----------+


Methods

~~~~~~~

+------------+------------------------------------+-----------------------------+
| Actions    | HTTP Request                       | Description                 |
+============+====================================+=============================+
| ``get``    | ``GET /submission/{id}``           | Get the Submission          |
+------------+------------------------------------+-----------------------------+
| ``update`` | ``PATCH (*PUT*) /submission/{id}`` | Post result or Update Lease |
+------------+------------------------------------+-----------------------------+


``get`` method
``````````````


parameters
++++++++++

+-----------+--------+----------------------+----------+
| Parameter | Type   | Description          | Required |
+===========+========+======================+==========+
| ``id``    | String | ID of the Submission | Yes      |
+-----------+--------+----------------------+----------+



response
++++++++

If successful, the method returns a Submission representation in the
response body.


``update`` method
`````````````````

The update method is used to post the result of the submission or to
update the lease time in case more time is required. The preferred
HTTP method is PATCH, but PUT is also supported. When PATCH is used
the submission representation can be partial, meaning that only the
fields that are going to be updated need to be present.

To post the result, update the ``state`` and ``result`` fields of the
Submission representation. The only possible values for the state
field are "SUCCESS" and "ERROR". No more updates are allowed after the
first one. Both fields must be present.

To update the lease, update the ``expiration`` field of the submission.
More updates are allowed after the first one.


parameters
++++++++++

+----------------+--------+--------------------------------+----------+----------------+
| Parameter      | Type   | Description                    | Required | Comment        |
+================+========+================================+==========+================+
| ``id``         | String | Name of the Queue              | Yes      |                |
+----------------+--------+--------------------------------+----------+----------------+
| ``submission`` | Object | Representation of a Submission | No       | Can be partial |
+----------------+--------+--------------------------------+----------+----------------+



response
++++++++

If successful, the method returns in a ``204 No Content`` status with no
response body.

If the request is malformed, or if one of the submission state or
result fields are missing, ``400 Bad Request`` error will be returned.

If the submission is already in a final state (SUCCESS or ERROR) and
has a result, a ``409 Conflict`` error will be returned.


Subscription
------------

A resource representing a subscription for notifications between a
queue and an endpoint.


Representation
~~~~~~~~~~~~~~

::

    {
      id: <String>,
      url: <String>,
      queue-name: <String>,
      queue-url: <String>,
      endpoint: <String>
    }


+----------------+--------+--------------------------------------------------------------------+------------+----------+
| Property       | Type   | Description                                                        | Access     | Optional |
+================+========+====================================================================+============+==========+
| ``id``         | String | Unique identifier for the Submission                               | Read       | No       |
+----------------+--------+--------------------------------------------------------------------+------------+----------+
| ``url``        | String | URL for the Submission                                             | Read       | No       |
+----------------+--------+--------------------------------------------------------------------+------------+----------+
| ``queue-name`` | String | ``READY`` \| ``LEASED`` \| ``SUCCESS`` \| ``ERROR`` \| ``EXPIRED`` | Read       | No       |
+----------------+--------+--------------------------------------------------------------------+------------+----------+
| ``queue-url``  | String | Timestamp in Unix Time when the submission was queued              | Read       | No       |
+----------------+--------+--------------------------------------------------------------------+------------+----------+
| ``endpoint``   | String | Timestamp in Unix Time when the lease will expire                  | Read-Write | No       |
+----------------+--------+--------------------------------------------------------------------+------------+----------+


Methods
~~~~~~~

+---------------+---------------------------------------------------+-----------------------------------+
| Actions       | HTTP Request                                      | Description                       | 
+===============+===================================================+===================================+
| ``subscribe`` | ``POST /queue/{name}/subscription``               | Subscribe to queue notifications. |
+---------------+---------------------------------------------------+-----------------------------------+
| ``get``       | ``GET /queue/{name}/subscription/{id}``           | Get subscription info.            |
+---------------+---------------------------------------------------+-----------------------------------+
| ``list``      | ``GET /queue/{name}/subscription``                | List all subscriptions.           |
+---------------+---------------------------------------------------+-----------------------------------+
| ``update``    | ``PATCH (*PUT*) /queue/{name}/subscription/{id}`` | Update subscription.              |
+---------------+---------------------------------------------------+-----------------------------------+
| ``delete``    | ``DELETE /queue/{name}/subscription/{id}``        | Delete subscription.              |
+---------------+---------------------------------------------------+-----------------------------------+


subscribe method
````````````````

Subscribe an endpoint to the specified queue. The endpoint will
receive periodic ``POST`` requests with the representation of the Queue.
The endpoint should reply with code ``204 Accepted`` if the notification
is valid.

The first notification after a subscription will have the ``length``
field set to zero. The reply to the first notification should be valid
for the subscription to be confirmed, otherwise it will be deleted.

If too many notifications are replied with an invalid code, and there
are no submissions being leased from the queue, the subscription will
be deleted and application will have to create a new one. A good
practice is to have application create a new subscription on startup.


parameters
++++++++++

+-----------+--------+-------------------+----------+
| Parameter | Type   | Description       | Required |
+===========+========+===================+==========+
| name      | String | Name of the Queue | Yes      |
+-----------+--------+-------------------+----------+



response
++++++++

If successful, the method returns a Subscription representation in the
response body. If a subscription to the same endpoint already exists,
a new one is created replacing the old one.


Problem Types
=============


CodeResponse
------------

CodeResponse problem response types, take one input from the student,
either a text string (usually source code), or a file. Both the
``payload`` and the ``result`` are JSON objects with the properties
described below.


Payload
~~~~~~~

::

    {
      student: <String>,
      problem: <String>,
    }

+-------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Property    | Type   | Description                                                                                                                                                        |
+=============+========+====================================================================================================================================================================+
| ``student`` | String | The student payload. A Base64 encoded string. Contains student's answer to the problem.                                                                            |
+-------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``problem`` | String | The problem payload. A string configured in the problem content that can contain any arbitrary value required by the instructor for checking the specific problem. |
+-------------+--------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------+


Result
~~~~~~

::

    {
      correct: <Boolean>,
      score: <Number>,
      msg: <String>
    }

+-------------+---------+---------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Property    | Type    | Description                                                                                                                                                   |
+=============+=========+===============================================================================================================================================================+
| ``correct`` | Boolean | Can the student answer be considered as correct or not.                                                                                                       |
+-------------+---------+---------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``score``   | Number  | A numeric value assigned to the answer. For partial credit, ``correct`` property must be ``true``. Values between 0.0 and 1.0 are encoraged but not required. |
+-------------+---------+---------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``msg``     | String  | An html string that will be shown to the student.                                                                                                             |
+-------------+---------+---------------------------------------------------------------------------------------------------------------------------------------------------------------+


Example
~~~~~~~

The Submission:

::

    Request:
    POST /checker/v1/queue/problem1.1/lease HTTP/1.1
    Host: api.edx.org
    ...
    
    Response:
    HTTP/1.1 201 Created
    ...
    Content-Type: application/json
    Content-Length: {length}
     
    {
        "submissions": [
            {
                "id": "AB1233",
                "type": "coderesponse",
                "url": "https://api.edx.org/checker/v1/submission/AB1233",
                "state": "LEASED",
                "enqueue": 1368459052,
                "expires": 1368459112,
                "payload": {
                    "student": "aGVsbG8gd29ybGQK",
                    "problem": "answer=\'hello world\'"
                }
            }
        ]
    }


The result:

::

    Request:
    PATCH /checker/v1/submission/AB1233 HTTP/1.1
    Host: api.edx.org
    ...
     
    {
        "state": "SUCCESS",
        "result": {
            "correct": true,
            "score": 1.0,
            "msg": "<p>Great! You got the right answer!</p>"
        
        } 
    }
    
     
    Response:
    HTTP/1.1 204 No Content
    ...


.. _RFC 4627: http://tools.ietf.org/html/rfc4627
.. _RFC 2617: http://www.ietf.org/rfc/rfc2617.txt
.. _RFC 2818: http://www.ietf.org/rfc/rfc2818.txt
.. _RFC 2616: http://tools.ietf.org/html/rfc2616

