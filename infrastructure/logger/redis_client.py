from core.interfaces.i_logger import IRobotLogger
import redis
import json


class RedisClient:
    def __init__(self, host: str, port: int, robot_logger: IRobotLogger, db=0):
        self.robot_logger = robot_logger
        self.is_redis_connected = False
        self.client = None
        self._connection_attempt(host, port, db)

    def _connection_attempt(self, host: str, port: int, db):
        """Попытка подключения к хосту. Проверяется только при инициализации."""
        try:
            self.client = redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)
            if self.client.ping():
                self.is_redis_connected = True
                self.robot_logger.info("Подключение к Redis успешно установлено.")
            else:
                self.is_redis_connected = False
                self.robot_logger.error("Ошибка подключения к Redis.")
        except redis.exceptions.ConnectionError as e:
            self.is_redis_connected = False
            self.robot_logger.error(f"Ошибка подключения к Redis: {e}")
        except Exception as e:
            self.robot_logger.error(f"Общая ошибка при подключении к Redis: {e}")

    def push_to_queue(self, queue_name: str, message: dict):
        """Добавить сообщение в очередь только если соединение активно."""
        if self.is_redis_connected:
            try:
                serialized_message = json.dumps(message)
                self.client.lpush(queue_name, serialized_message)
            except Exception as e:
                self.robot_logger.error(f'Ошибка отправки сообщения в очередь Redis: {e}')
        else:
            self.robot_logger.error('Не удалось подключиться к Redis. Сообщение не отправлено в очередь.')

    def get_from_queue(self, queue_name: str):
        """Извлечь сообщение из очереди только если соединение активно."""
        if self.is_redis_connected:
            return self.client.rpop(queue_name)
        else:
            self.robot_logger.error('Не удалось подключиться к Redis. Не удалось извлечь сообщение из очереди.')
            return None
