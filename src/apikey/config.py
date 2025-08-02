"""
config.py
Configuration settings for API key management
"""
from config import get_config

API_KEY_EXPIRE_TIME = 2592000 # 30 days expiration for API keys
# API_KEY_EXPIRE_TIME = 1 # debugging purpose, set to 1 second for quick testing


def get_secret_key():
    """Get secret key from configuration"""
    config = get_config()
    return config.get_secret_key()

def get_algorithm():
    """Get JWT algorithm from configuration"""
    config = get_config()
    return config.get_algorithm() 