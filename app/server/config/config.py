import os
from dotenv import load_dotenv

load_dotenv()

# Defaults
PROXY_API_PREFIX = '/cph'
APP_TITLE = 'Common Mono Service'
APP_VERSION = '1.0.0'

# Environment Variables
MONGO_URI = os.getenv('MONGO_URI')
DOC_USERNAME = os.getenv('DOC_USERNAME')
DOC_PASSWORD = os.getenv('DOC_PASSWORD')
