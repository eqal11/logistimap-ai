import os
os.environ["DATA_MODE"] = "fixture"
os.environ["REQUEST_LIMIT_PER_MINUTE"] = "10000"
# Offline tests must never use credentials from backend/.env.
for key in ["DATABASE_URL", "DATABASE_HOST", "DATABASE_USER", "DATABASE_PASSWORD"]:
    os.environ[key] = ""


import pytest
from fastapi.testclient import TestClient
from app.main import app, requests_by_ip


@pytest.fixture()
def client():
    requests_by_ip.clear()
    with TestClient(app) as test_client:
        yield test_client
