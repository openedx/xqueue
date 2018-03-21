# External Grader Load Testing

You can use the integration testing framework to load test external
graders using XQueue.

The tests use multi-mechanize to run the tests, which interact
with XQueue using the integration testing framework.

## Setting Up XQueue for Load Testing

You can run load tests of an external server while running
XQueue locally.

1. Load user login information (see CONFIG.md)
2. If you want XQueue to push submissions to your external grader, then
ensure that `xqueue/settings.py` has `XQUEUES = { QUEUE_NAME: QUEUE_URL }`
3. Start XQueue: `./run.sh`
4. Start workers: `python manage.py run_consumer`
5. Run your load test.  If you are using multi-mechanize, the command
is `multimech-run PROJECT_NAME`.  
**Note**: You can configure multi-mechanize by updating the `config.cfg` file 
in the test directory.
