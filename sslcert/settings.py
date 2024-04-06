from typing import Type

from pydantic import BaseModel
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # json_file="config.json",
        # json_file_encoding="utf-8",
        extra="ignore",
    )

    #  acme.sh exported env
    CERT_PATH: str | None = None
    CERT_KEY_PATH: str | None = None
    CA_CERT_PATH: str | None = None
    CERT_FULLCHAIN_PATH: str | None = None
    Le_Domain: str | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            JsonConfigSettingsSource(settings_cls),
        )


class DomainSetting(BaseModel):
    AliAccessKeyId: str
    AliAccessKeySecret: str

    CDN_DOMAINS: list[str] = []
    DCDN_DOMAINS: list[str] = []


class Config(BaseModel):
    CERT_PATH: str | None = None
    CERT_KEY_PATH: str | None = None
    CA_CERT_PATH: str | None = None
    CERT_FULLCHAIN_PATH: str | None = None
    Le_Domain: str | None = None

    domains: dict[str, DomainSetting]  # key is Le_Domain


settings = Settings()  # type: ignore
