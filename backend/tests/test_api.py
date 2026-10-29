import pytest
from ldap3.core.exceptions import LDAPBindError, LDAPSocketOpenError
from pydantic import ValidationError

from app import ad_import
from app.config import DEFAULT_AD_USER_FILTER, Settings
from app.routers import auth as auth_router

from .conftest import AD_OUS, AD_USERS, DEV, login, user


def _find(nodes, name):
    for n in nodes:
        if n["name"] == name:
            return n
        found = _find(n["children"], name)
        if found:
            return found
    return None


def test_search_is_case_insensitive_for_cyrillic(admin_client):
    for q in ("иванов", "ИВАНОВ", "Иванов"):
        r = admin_client.get("/api/departments/search", params={"q": q})
        assert r.status_code == 200
        assert [e["login"] for e in r.json()["employees"]] == ["ivanov"], q

    r = admin_client.get("/api/departments/search", params={"q": "разработка"})
    assert [d["name"] for d in r.json()["departments"]] == ["Разработка"]


def test_tree_has_hierarchy_counts_and_heads(admin_client):
    tree = admin_client.get("/api/departments/tree").json()
    it = _find(tree, "ИТ")
    dev = _find(tree, "Разработка")
    assert dev in it["children"]
    assert dev["employees_count"] == 2
    assert dev["head_login"] == "boss"


def test_failed_import_keeps_previous_data(admin_client, monkeypatch):
    broken = AD_USERS + [user("dup", "Иванов Иван", DEV)]  # duplicate DN
    monkeypatch.setattr(ad_import, "_fetch_from_ad_sync", lambda: (broken, dict(AD_OUS)))

    r = admin_client.post("/api/admin/import")
    assert r.status_code == 500
    assert "Иванов" not in r.json()["detail"]

    status = admin_client.get("/api/admin/status").json()
    assert status == {"departments": 2, "employees": 3}


def test_default_user_filter_excludes_disabled_and_computers():
    assert "userAccountControl:1.2.840.113556.1.4.803:=2" in DEFAULT_AD_USER_FILTER
    assert "objectCategory=person" in DEFAULT_AD_USER_FILTER


def test_login_sets_httponly_cookie_and_normalizes_login(client, monkeypatch):
    seen = []
    monkeypatch.setattr(auth_router, "_bind_check", lambda upn, pw: seen.append(upn))

    data = login(client, "RVK\\Admin")
    assert data == {"username": "admin", "is_admin": True}
    assert "access_token" not in data
    assert seen == ["admin@RVK.local"]

    cookie = client.cookies.get("phonebook_token")
    assert cookie

    login(client, "Ivanov@RVK.local")
    assert seen[-1] == "ivanov@RVK.local"
    assert client.get("/api/auth/me").json() == {"username": "ivanov", "is_admin": False}


def test_logout_and_unauthenticated_access(client):
    login(client)
    assert client.get("/api/departments/tree").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/departments/tree").status_code == 401


def test_non_admin_cannot_import(client):
    login(client, "ivanov")
    assert client.post("/api/admin/import").status_code == 403


def test_bad_password_and_ad_errors(client, monkeypatch):
    def bad(upn, pw):
        raise LDAPBindError("invalidCredentials")

    monkeypatch.setattr(auth_router, "_bind_check", bad)
    r = client.post("/api/auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 401

    r = client.post("/api/auth/login", json={"username": "x", "password": ""})
    assert r.status_code == 422

    def down(upn, pw):
        raise LDAPSocketOpenError("socket ssl wrapping error: 10.0.0.1")

    monkeypatch.setattr(auth_router, "_bind_check", down)
    r = client.post("/api/auth/login", json={"username": "x", "password": "y"})
    assert r.status_code == 503
    assert "10.0.0.1" not in r.json()["detail"]


@pytest.mark.parametrize("secret", ["change-me", "short", ""])
def test_insecure_jwt_secret_rejected(secret):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret=secret)


def test_sync_sqlite_url_is_converted():
    s = Settings(_env_file=None, database_url="sqlite:///./x.db")
    assert s.database_url == "sqlite+aiosqlite:///./x.db"
