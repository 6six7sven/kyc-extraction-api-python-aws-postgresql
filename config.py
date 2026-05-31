from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    s3_bucket_name: str = "my-ocr-bucket"
    database_url: str = "postgresql://postgres:password@localhost:5432/kyc_db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "my-super-secret-jwt-key"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()