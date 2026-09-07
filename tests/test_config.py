from content_os.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "Metabolic Health Content OS"
    assert settings.app_environment == "development"
    assert settings.app_version == "0.1.0"
    assert settings.database_url == "sqlite:///./content_os.db"
