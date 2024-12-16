from settings import Settings, BASE_DIR, BUFFER_DIR, LOG_FILE, NETWORK_DISK, REDIS_HOST, REDIS_PORT
from app.app import AppCoordinator
from infrastructure import SQLAlchemySettings, RobotLogger, RedisClient


if __name__ == '__main__':
    """Main driver."""
    settings = Settings()
    sql_aclhemy_settings = SQLAlchemySettings(settings.alchemy_db.url_database)
    robot_logger = RobotLogger(LOG_FILE)

    redis_client = RedisClient(
        REDIS_HOST, REDIS_PORT, robot_logger
    )
    robot_logger.redis_client = redis_client

    app_coordinator = AppCoordinator(
        settings,
        BASE_DIR,
        BUFFER_DIR,
        NETWORK_DISK,
        sql_aclhemy_settings,
        robot_logger
    )
    app_coordinator.robot_process()
