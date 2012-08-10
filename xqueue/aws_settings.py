from settings import *

ENV_ROOT = ROOT_PATH.dirname()

with open(ENV_ROOT / "env.json") as env_file:
    ENV_TOKENS = json.load(env_file)

XQUEUES = ENV_TOKENS['XQUEUES']
XQUEUE_WORKERS_PER_QUEUE = ENV_TOKENS['XQUEUE_WORKERS_PER_QUEUE']

with open(ENV_ROOT / "auth.json") as auth_file:
    AUTH_TOKENS = json.load(auth_file)

DATABASES = AUTH_TOKENS['DATABASES']

AWS_ACCESS_KEY = AUTH_TOKENS['AWS_ACCESS_KEY']
AWS_SECRET_KEY = AUTH_TOKENS['AWS_SECRET_KEY']
