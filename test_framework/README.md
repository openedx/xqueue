# Integration Test Framework

A framework for handling setup of XQueue for integration tests.  These
are used by the tests in `queue/tests` to:

* Abstract setup / teardown of the XQueue.  For example, there is a 
`start_workers()` method that starts RabbitMQ workers (consumers)
running locally.

* Stub out parts of the system.  For example, some of the tests run an "external"
grading service that listens and responds on a local port.

The framework is defined in `integration_framework.py` and used
by some of the tests in `queue/tests/`

# Running Tests

Integration tests run as part of the test suite.  To run the suite,
use:

     rake test

in the base `xqueue` directory.

# Authentication Information

Some tests may require authentication information that, for security reasons,
should be kept separate from the repository.  For example, you might write
an integration test that uses an external service that requires login.  Or
you might configure the tests to use an external RabbitMQ server when
running the tests on a continuous integration server.

For this reason, `xqueue/test_settings.py` has a mechanism for loading
auth tokens from a JSON file called `test_env.json`.  When the tests run,
the test suite searches:

1. The directory specified by the environment variable `JENKINS_CONFIG_DIR`,
if provided

2. One directory above the base `xqueue` directory.

Tests that require authentication to run should raise a SkipTest exception
if the authentication information is not provided.  See the integration test 
`queue/tests/test_matlab_grader.py` for an example.


# RabbitMQ Dependency

Integration tests require access to a RabbitMQ broker.  By default, the tests
assume a RabbitMQ broker is running locally, and that it uses the default
username ("guest") and password (also "guest").

To start a local RabbitMQ broker, use:

     rabbitmq-server
     rabbitmqctl start_app

See [the RabbitMQ docs](http://www.rabbitmq.com/admin-guide.html) for information
on installing and running RabbitMQ.

You can override these settings in `test_env.json` to use an external RabbitMQ broker.
See `xqueue/test_settings.py` for details.
