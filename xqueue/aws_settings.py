import logging

from production import *

logger = logging.getLogger(__name__)
logger.error("aws_settings is deprecated, please use xqueue.production instead")
