# External Grader Load Testing

You can use the integration testing framework to load test external
graders using XQueue.

The tests use multi-mechanize to run the tests, which interact
with XQueue using the integration testing framework.

## Setting Up XQueue for Load Testing

You can run load tests of an external server while running
XQueue locally.

1. Load user login information (see CONFIG.md)
2. Ensure that `xqueue/settings.py` contains `RABBITMQ_USER` and `RABBITMQ_PASS`,
which can both be set to `guest` (the default for rabbitmq)
3. If you want XQueue to push submissions to your external grader, then
ensure that `xqueue/settings.py` has `XQUEUES = { QUEUE_NAME: QUEUE_URL }`
4. Start rabbitmq locally: `rabbitmq-server` and `rabbitmqctl start_app`
5. Start XQueue: `./run.sh`
6. Start rabbit workers: `python manage.py run_consumer`
**NOTE:** currently this command fails when running locally on Mac OS X
because of a conflict between pika (rabbitmq python wrapper) and
Python's multithreading library.  You can fix the issue by changing
`Worker` in `queue/consumer.py` to subclass `threading.Thread` instead 
of `multiprocessing.Process`.
7. Run your load test.  If you are using multi-mechanize, the command
is `multimech-run PROJECT_NAME`.  
**Note**: You can configure multi-mechanize by updating the `config.cfg` file 
in the test directory.
