from pydantic import BaseSettings


class Settings(BaseSettings):
    SENTRY_DSN: str = "https://sentry.io/organization/project/project-id"
    ENVIRONMENT: str = "development"
    JWT_ALGORITHM: str = "RS256"
    JWT_PUBLIC_KEY: str = ""
    CLOUD_LOGGING: str = "true"


settings = Settings()
