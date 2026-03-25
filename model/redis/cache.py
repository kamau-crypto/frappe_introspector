# Cache
import json
from functools import wraps

from flask import g, request

from model.redis.cache_manager import CacheManager


def cache_result(key_prefix, ttl=300 ):
    """ Decorator function to cache results of a function or operation in Redis. 
    """
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build Cache key from prefix and arguements
            # example "user: 123" for get_user(123)
            module = request.args.get("module", "") if request.args else ""
            doctype_name = request.view_args.get("doctype_name", module) if request.view_args else module
            cache_key = f"{key_prefix}:{doctype_name}"
            cache= CacheManager(g.redis)
            #
            # Try to get the cached result as keys
            cached = cache.get(cache_key)
            if cached:
                return cached
            #
            # Execute function to cache results
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl, tags=[doctype_name])
            return result
        return wrapper
    return decorator


