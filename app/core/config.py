from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Skill Recommender"
    VERSION: str

    @property
    def API_V1_STR(self) -> str:
        return f"/api/v{self.VERSION}"

    # Database settings
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgres://{self.DB_USER}:{self.DB_PASSWORD}@"
            f"{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_CONFIG(self) -> dict:
        return {
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg",
                    "credentials": {
                        "database": self.DB_NAME,
                        "host": self.DB_HOST,
                        "password": self.DB_PASSWORD,
                        "port": self.DB_PORT,
                        "user": self.DB_USER,
                        "server_settings": {
                            "timezone": "UTC",
                            "datestyle": "ISO, DMY"
                        }
                    }
                }
            },
            "apps": {
                "models": {
                    "models": ["app.models"],
                    "default_connection": "default",
                }
            }
        }

    # JWT settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
