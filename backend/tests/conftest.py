import os
import tempfile
from pathlib import Path

import pytest

_DB_DIR = tempfile.mkdtemp()
os.environ.update(
    {
        "AD_SERVER": "ldaps://dc.test.local",
        "AD_USER": "svc@test.local",
        "AD_PASSWORD": "x",
        "AD_SEARCH_BASE": "DC=rvk,DC=local",
        "AD_DEPARTMENTS_BASE": "OU=Company,DC=rvk,DC=local",
        "AD_DOMAIN": "RVK.local",
        "JWT_SECRET": "test-secret-" + "x" * 40,
        "ADMIN_USERS": "admin",
        "DATABASE_URL": "sqlite:///" + str(Path(_DB_DIR) / "test.db").replace("\\", "/"),
    }
)

from fastapi.testclient import TestClient  # noqa: E402

from app import ad_import  # noqa: E402
from app.main import app  # noqa: E402
from app.routers import auth as auth_router  # noqa: E402

BASE = "OU=Company,DC=rvk,DC=local"


def user(login, cn, ou_path, manager=None, phone=None, title=None):
    dn = f"CN={cn},{ou_path}"
    return {
        "sAMAccountName": login,
        "cn": cn,
        "distinguishedName": dn,
        "manager": manager,
        "telephoneNumber": phone,
        "title": title,
    }


IT = f"OU=ИТ,{BASE}"
DEV = f"OU=Разработка,{IT}"

AD_USERS = [
    user("boss", "Петров Пётр", IT, title="Директор по ИТ"),
    user("ivanov", "Иванов Иван", DEV, manager=f"CN=Петров Пётр,{IT}", phone="+7 (423) 111-22-33"),
    user("sidorov", "Сидоров Сидор", DEV, manager=f"CN=Петров Пётр,{IT}"),
]
AD_OUS = {IT: "ИТ", DEV: "Разработка"}


@pytest.fixture
def client(monkeypatch):
    auth_router.login_limiter.clear()
    monkeypatch.setattr(auth_router, "_bind_check", lambda upn, pw: None)
    monkeypatch.setattr(
        ad_import,
        "_fetch_from_ad_sync",
        lambda: ([dict(u) for u in AD_USERS], dict(AD_OUS)),
    )
    with TestClient(app) as c:
        yield c


def login(client, username="admin"):
    r = client.post("/api/auth/login", json={"username": username, "password": "pw"})
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def admin_client(client):
    login(client, "admin")
    r = client.post("/api/admin/import")
    assert r.status_code == 200, r.text
    return client
