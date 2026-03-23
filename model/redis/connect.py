import os

from redis import ConnectionPool, Redis


def connect():
    """ A simple connection to redis, for testing purposes."""
    redis_client= Redis(host=os.getenv("REDIS_HOST", "localhost"), 
        port=int(os.getenv("REDIS_PORT", 6379)), 
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
        )
    return redis_client

class RedisConfig:
    """ Connection pool for redis, suitable for a production environment with multiple workers."""
    pool = ConnectionPool(host=os.getenv("REDIS_HOST", "localhost"), 
        port=int(os.getenv("REDIS_PORT", 6379)), 
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
        max_connections=4, # Set a resonable limit for connection based on the worker count for production environment
        socket_timeout=5, # Set a timeout for socket operations to prevent hanging in case of connection issues
        retry_on_timeout=True, # Enable retry on timeout to improve resilience in case of transient network issues
        socket_connect_timeout=5 # Set a timeout for connection attempts to prevent hanging in case of connection issues
    )

def check_redis_connection():
    try:
        redis_client = connect()
        redis_client.ping()
        return{
            "status": "success",
            "message": "Connected to Redis successfully."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to Redis: {e}"}, 503
        
def get_redis_client():
    """ Get a redis client from the connection pool."""
    return Redis(connection_pool=RedisConfig.pool)

# When working with redis, It can be used for different purposes in the application.
# 1. Simple Caching
# 2. 

