import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the Module_B directory (parent of app/)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


def get_env(name, default=None):
    """Get environment variable with fallback to default"""
    value = os.environ.get(name)
    return value if value not in (None, "") else default


def get_db_settings():
    """Get main database configuration from .env file"""
    return {
        "host": get_env("DB_HOST", "localhost"),
        "user": get_env("DB_USER", "root"),
        "password": get_env("DB_PASSWORD", ""),
        "database": get_env("DB_NAME", "dms_db"),
    }


def get_shard_settings():
    """Get shard database configuration from .env file"""
    return {
        "host": get_env("SHARD_HOST", "10.0.116.184"),
        "user": get_env("SHARD_DB_USER", "root"),
        "password": get_env("SHARD_DB_PASSWORD", ""),
        "database": get_env("SHARD_DB_NAME", "dms_db"),
        "port_0": int(get_env("SHARD_PORT_0", 3307)),
        "port_1": int(get_env("SHARD_PORT_1", 3308)),
        "port_2": int(get_env("SHARD_PORT_2", 3309)),
    }


def get_jwt_secret():
    """Get JWT secret from .env file"""
    return get_env("SECRET_KEY", "dev-secret-key")
