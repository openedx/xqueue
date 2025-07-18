⛔️ WARNING
==========

This repository is under-maintained. We are not fixing bugs or developing new features for it. We hope to deprecate it officially in October of 2024. For updates, `follow along on the DEPR ticket <https://github.com/openedx/public-engineering/issues/286>`_.

Although we have stopped integrating new contributions, we always appreciate security disclosures and patches sent to security@openedx.org

xqueue
======

XQueue defines an interface for the LMS to communicate with external
grader services.  For example, when a student submits a problem in the LMS,
it gets sent to the XQueue.  The XQueue then has the problem graded
by an external service and sends the response back to the LMS.

How the LMS Interacts with the XQueue
-------------------------------------

1. The LMS pushes student submissions to the XQueue with an HTTP POST request to
the URL `/xqueue/submit`.  The submission contains a callback URL indicating
where the graded response should be sent.

2. When the submission has been graded, the XQueue pushes a response back
to the LMS with an HTTP POST request to the callback URL.

How External Graders Interact with the XQueue
---------------------------------------------

There are two ways kinds of grading services: passive and active.  These
interact with the XQueue in different ways.

Passive Graders (aka Push Graders)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Passive graders wait for the XQueue to send them submissions.  They then
respond synchronously with a graded response.

1. The LMS sends messages to a particular queue.

2. XQueue checks its settings and finds that the queue has a URL associated
with it.  XQueue forwards the message to that URL.

3. The passive grader receives a POST request from the XQueue and
responds synchronously with the graded response.

4. XQueue forwards the graded response to the callback URL the LMS
provided in its original message.

Active Graders (aka Pull Graders)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Active graders pull messages off the XQueue and push responses back to the XQueue.

1. The test client sends messages to a particular queue.

2. The active grader polls the XQueue using a REST-like interface.  When it
receives a submission, it pushes a response back to the XQueue, also using
a REST-like interface.

If a submission is retrieved but not graded, it will be available in the queue
later following the SUBMISSION_PROCESSING_DELAY when it is requeued.

3. XQueue pushes the response back to the LMS.

Local Testing
-------------

XQueue is now available as a docker image used as part of Docker Devstack.
You can start and provision it by using xqueue specific commands configured in
your `devstack` directory

    make dev.provision.xqueue
    make dev.up.xqueue

XQueue will use the shared MySQL image.

Tests
-----

You can run the unit/integration test suite using:

    make test

after connecting to your container on Docker Devstack

    make xqueue-shell
    make test

License
-------

The code in this repository is licensed under version 3 of the AGPL unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How to Contribute
-----------------

Contributions are very welcome. The easiest way is to fork this repo, and then
make a pull request from your fork. The first time you make a pull request, you
may be asked to sign a Contributor Agreement.

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@openedx.org

Mailing List and other support options
--------------------------------------

https://open.edx.org/getting-help
