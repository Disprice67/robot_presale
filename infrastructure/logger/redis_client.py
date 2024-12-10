import redis
import json


class RedisClient:
    def __init__(self, host, port, db=0):
        self.client = redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)

    def push_to_queue(self, queue_name: str, message: dict):
        """Добавить сообщение в очередь."""
        serialized_message = json.dumps(message)
        self.client.lpush(queue_name, serialized_message)

    def get_from_queue(self, queue_name: str):
        """Извлечь сообщение из очереди."""
        return self.client.rpop(queue_name)
