"""
Configuration settings for Gmail automation
"""
import os

# Gmail API Settings
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
GMAIL_QUERY = "from:accounts.google.com"
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'

# API Rate Limiting
MAX_RETRIES = 5
INITIAL_BACKOFF = 1  # seconds
MAX_BACKOFF = 32  # seconds
BATCH_SIZE = 100  # Number of messages to process in batch

# Selenium Settings
HEADLESS_MODE = True
PAGE_LOAD_TIMEOUT = 10  # seconds
ELEMENT_WAIT_TIMEOUT = 5  # seconds
POST_CLICK_WAIT = 1  # seconds

# Regex Pattern for removal links
REMOVAL_LINK_PATTERN = r'https://accounts\.google\.com/AccountDisavow\?[\w=&-]+'

# Logging
LOG_FILE = 'automation.log'
LOG_LEVEL = 'INFO'

# Parallel Processing
MAX_WORKERS = 3  # Number of parallel browser instances
ENABLE_PARALLEL = False  # Set to True to enable parallel processing

# Made with Bob
