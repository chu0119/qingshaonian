import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # 环境: demo / development / production
    APP_ENV: str = os.getenv("APP_ENV", "demo")

    # 数据库类型: sqlite 或 mysql
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")

    # MySQL配置
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_NAME: str = os.getenv("DB_NAME", "qingshaonian")
    DB_USER: str = os.getenv("DB_USER", "")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "mysql":
            return (
                f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
            )
        return "sqlite:///./qingshaonian.db"

    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))

    # 系统
    APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")
    APP_NAME: str = os.getenv("APP_NAME", "青少年风险防范测评管理系统")

    # 管理员
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "")
    PLATFORM_ADMIN_USERNAME: str = os.getenv("PLATFORM_ADMIN_USERNAME", "")
    PLATFORM_ADMIN_PASSWORD: str = os.getenv("PLATFORM_ADMIN_PASSWORD", "")

    # 调试
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    INIT_BUILTIN_QUESTIONNAIRES: bool = os.getenv(
        "INIT_BUILTIN_QUESTIONNAIRES",
        "true" if os.getenv("APP_ENV", "demo").lower() in {"demo", "development"} else "false",
    ).lower() == "true"
    INIT_DEMO_DATA: bool = os.getenv("INIT_DEMO_DATA", "false").lower() == "true"

    # 可选外部服务开关。生产环境只有显式启用时才强制校验密钥。
    SMS_ENABLED: bool = os.getenv("SMS_ENABLED", "false").lower() == "true"
    SMS_API_URL: str = os.getenv("SMS_API_URL", "")
    SMS_APP_KEY: str = os.getenv("SMS_APP_KEY", "")
    AI_ENABLED: bool = os.getenv("AI_ENABLED", "false").lower() == "true"
    AI_API_URL: str = os.getenv("AI_API_URL", "")
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")

    class Config:
        env_file = ".env"


settings = Settings()


WEAK_SECRET_VALUES = {
    "",
    "default-secret-change-me",
    "change-me-to-a-random-secret-key-in-production",
    "secret",
    "test",
}

WEAK_PASSWORD_VALUES = {"", "admin", "admin123", "123456", "password", "padm123"}


def validate_production_settings(current: Settings = settings) -> None:
    """Fail fast when production is started with unsafe or missing configuration."""
    if current.APP_ENV.lower() != "production":
        return

    errors: list[str] = []
    if current.DEBUG:
        errors.append("DEBUG must be false in production")
    if current.JWT_SECRET_KEY in WEAK_SECRET_VALUES or len(current.JWT_SECRET_KEY) < 32:
        errors.append("JWT_SECRET_KEY must be a non-default random secret with at least 32 characters")
    if current.DB_TYPE != "mysql":
        errors.append("DB_TYPE must be mysql in production")
    if not current.DB_HOST or not current.DB_NAME or not current.DB_USER or not current.DB_PASSWORD:
        errors.append("DB_HOST, DB_NAME, DB_USER and DB_PASSWORD are required in production")
    if current.ADMIN_PASSWORD in WEAK_PASSWORD_VALUES or len(current.ADMIN_PASSWORD) < 10:
        errors.append("ADMIN_PASSWORD must be configured and stronger than the demo default")
    if current.PLATFORM_ADMIN_PASSWORD in WEAK_PASSWORD_VALUES or len(current.PLATFORM_ADMIN_PASSWORD) < 10:
        errors.append("PLATFORM_ADMIN_PASSWORD must be configured and stronger than the demo default")
    if current.SMS_ENABLED and (not current.SMS_API_URL or not current.SMS_APP_KEY):
        errors.append("SMS_API_URL and SMS_APP_KEY are required when SMS_ENABLED=true")
    if current.AI_ENABLED and (not current.AI_API_URL or not current.AI_API_KEY):
        errors.append("AI_API_URL and AI_API_KEY are required when AI_ENABLED=true")

    if errors:
        raise RuntimeError("Production configuration check failed: " + "; ".join(errors))
