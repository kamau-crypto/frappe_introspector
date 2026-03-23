# Cache
import json
from functools import wraps

from flask import g


def cache_result(key_prefix, ttl=300 ):
    """ Decorator function to cache results of a function or operation in Redis. 
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build Cache key from prefix and arguements
            # example "user: 123" for get_user(123)
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
            #
            # Try to get the cached result
            cached = g.redis.get(cache_key)
            if cached:
                return json.loads(cached)
            #
            # Execute function to cache results
            result = func(*args, **kwargs)
            g.redis.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator


