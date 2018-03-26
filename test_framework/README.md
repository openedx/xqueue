# Integration Test Framework

A framework for handling setup of XQueue for integration tests.  These
are used by the tests in `queue/tests` to:

* Abstract setup / teardown of the XQueue.  For example, there is a 
`start_workers()` method that starts (consumers) running locally.

* Stub out parts of the system.  For example, some of the tests run an "external"
grading service that listens and responds on a local port.

The framework is defined in `integration_framework.py` and used
by some of the tests in `queue/tests/`

# Running Tests

Integration tests run as part of the test suite.  To run the suite,
use:

     make xqueue-shell
     make test

in the base Docker Devstack directory and it will run from your xqueue checkout.

# Authentication Information

Some tests may require authentication information that, for security reasons,
should be kept separate from the repository.  For example, you might write
an integration test that uses an external service that requires login.

For this reason, `xqueue/test_settings.py` has a mechanism for loading
auth tokens from a JSON file called `test_env.json`.  When the tests run,
the test suite searches:

1. The directory specified by the environment variable `JENKINS_CONFIG_DIR`,
if provided

2. One directory above the base `xqueue` directory.

Tests that require authentication to run should raise a SkipTest exception
if the authentication information is not provided.  See the integration test 
`queue/tests/test_matlab_grader.py` for an example.
