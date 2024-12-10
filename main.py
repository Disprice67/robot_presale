from settings import Settings, BASE_DIR, BUFFER_DIR, LOG_FILE, NETWORK_DISK
from app.app import AppCoordinator
from infrastructure import SQLAlchemySettings, RobotLogger, RedisClient


if __name__ == '__main__':
    """Main driver."""
    settings = Settings()
    sql_aclhemy_settings = SQLAlchemySettings(settings.alchemy_db.url_database)
    redis_client = RedisClient(
        settings.redis_settings.redis_url, settings.redis_settings.redis_port
    )
    robot_logger = RobotLogger(LOG_FILE, redis_client)

    app_coordinator = AppCoordinator(
        settings,
        BASE_DIR,
        BUFFER_DIR,
        NETWORK_DISK,
        sql_aclhemy_settings,
        robot_logger
    )
    app_coordinator.robot_process()
