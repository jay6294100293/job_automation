import redis

try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    ping_result = r.ping()
    print(f"✅ Successfully connected to Redis! Ping result: {ping_result}")
    print(f"Redis version: {r.info('server')['redis_version']}")
except redis.exceptions.ConnectionError as e:
    print(f"❌ Redis connection error: {e}")
    print("Make sure Docker is running and the Redis container is started")