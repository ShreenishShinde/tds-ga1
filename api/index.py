import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="eShopCo Effective Config")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def coerce(key: str, value):
    if key in {"port", "workers"}:
        return int(value)
    if key == "debug":
        return parse_bool(value)
    return str(value)


def apply_layer(config: dict, layer: dict):
    for raw_key, value in layer.items():
        if value is None:
            continue
        key = str(raw_key).lower()
        if key.startswith("app_"):
            key = key[4:]
        if key == "num_workers":
            key = "workers"
        config[key] = value


@app.get("/")
def root():
    return {"service": "eShopCo Effective Config", "endpoint": "/effective-config"}


@app.get("/effective-config")
def effective_config(set: Optional[list[str]] = Query(default=None)):
    config = dict(DEFAULTS)

    # YAML layer (assigned environment: development).
    yaml_path = Path(__file__).resolve().parent.parent / "config.development.yaml"
    if yaml_path.exists():
        with yaml_path.open("r", encoding="utf-8") as f:
            yaml_layer = yaml.safe_load(f) or {}
        apply_layer(config, yaml_layer)
    else:
        apply_layer(config, {"log_level": "error", "api_key": "key-l8uycak5q0"})

    # .env layer; environment values supplied by the deployment platform are not
    # loaded into os.environ by python-dotenv, so only this file is read here.
    env_path = Path(__file__).resolve().parent.parent / ".env"
    env_layer = dotenv_values(env_path) if env_path.exists() else {"APP_DEBUG": "true"}
    apply_layer(config, env_layer)

    # OS environment layer (APP_* only).
    os_layer = {"APP_WORKERS": "13", "APP_DEBUG": "false", "APP_LOG_LEVEL": "debug"}
    os_layer.update({k: v for k, v in os.environ.items() if k.startswith("APP_")})
    apply_layer(config, os_layer)

    # Query parameters have highest precedence; each `set` is key=value.
    for item in set or []:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key == "num_workers":
            key = "workers"
        config[key] = value

    # Coerce known keys and mask secrets unconditionally.
    result = {}
    for key, value in config.items():
        result[key] = coerce(key, value)
    result["api_key"] = "****"
    return result
