from app.core.config import Settings


def test_dev_allows_default_secret():
    assert Settings(app_env="dev", jwt_secret="change-me-in-production").insecure_settings() == []


def test_production_rejects_default_secret_and_wildcard_cors():
    s = Settings(app_env="production", jwt_secret="change-me-in-production", cors_origins="*")
    problems = s.insecure_settings()
    assert len(problems) == 2


def test_production_accepts_strong_secret_and_explicit_origin():
    s = Settings(app_env="production", jwt_secret="x" * 48, cors_origins="https://armor.example")
    assert s.insecure_settings() == []
