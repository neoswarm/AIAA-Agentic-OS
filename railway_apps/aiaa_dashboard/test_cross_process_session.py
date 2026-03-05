#!/usr/bin/env python3
"""Cross-process verification for dashboard session-cookie visibility."""

import hashlib
import multiprocessing
import os
import sys
import tempfile
from http.cookies import SimpleCookie
from pathlib import Path


DASHBOARD_DIR = Path(__file__).parent.resolve()


def _build_env(db_path: str, password_hash: str, secret_key: str) -> dict:
    """Build isolated env vars for one dashboard process."""
    env = os.environ.copy()
    env.update(
        {
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "false",
            "DASHBOARD_USERNAME": "testadmin",
            "DASHBOARD_PASSWORD_HASH": password_hash,
            "FLASK_SECRET_KEY": secret_key,
            "DB_PATH": db_path,
        }
    )
    return env


def _extract_session_cookie(set_cookie_headers) -> str:
    """Extract the Flask session cookie value from response headers."""
    for header in set_cookie_headers:
        cookie = SimpleCookie()
        cookie.load(header)
        if "session" in cookie:
            return cookie["session"].value
    return ""


def _login_in_child(conn, env: dict, password: str) -> None:
    """Child process: login and return the signed session cookie."""
    try:
        os.environ.update(env)
        sys.path.insert(0, str(DASHBOARD_DIR))
        from app import create_app

        app = create_app()
        app.config["TESTING"] = True
        app.config["SESSION_COOKIE_SECURE"] = False

        client = app.test_client()
        response = client.post(
            "/login",
            data={"username": "testadmin", "password": password},
            follow_redirects=False,
        )
        session_cookie = _extract_session_cookie(response.headers.getlist("Set-Cookie"))
        conn.send(
            {
                "ok": True,
                "status_code": response.status_code,
                "session_cookie": session_cookie,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive guard for child process
        conn.send({"ok": False, "error": repr(exc)})
    finally:
        conn.close()


def _validate_in_child(conn, env: dict, session_cookie: str) -> None:
    """Child process: verify cookie-auth succeeds on a separate app instance."""
    try:
        os.environ.update(env)
        sys.path.insert(0, str(DASHBOARD_DIR))
        from app import create_app

        app = create_app()
        app.config["TESTING"] = True
        app.config["SESSION_COOKIE_SECURE"] = False

        client = app.test_client()
        unauth = client.get("/api/v2/settings/api-keys/status")
        client.set_cookie("session", session_cookie, domain="localhost")
        auth = client.get("/api/v2/settings/api-keys/status")
        conn.send(
            {
                "ok": True,
                "unauth_status": unauth.status_code,
                "auth_status": auth.status_code,
                "auth_payload": auth.get_json(silent=True) or {},
            }
        )
    except Exception as exc:  # pragma: no cover - defensive guard for child process
        conn.send({"ok": False, "error": repr(exc)})
    finally:
        conn.close()


def _run_child(target, *args) -> dict:
    """Run target in a separate process and return its result payload."""
    recv_conn, send_conn = multiprocessing.Pipe(duplex=False)
    process = multiprocessing.Process(target=target, args=(send_conn, *args))
    process.start()
    send_conn.close()

    if not recv_conn.poll(20):
        process.terminate()
        process.join(5)
        raise AssertionError(f"Child process timed out for {target.__name__}")

    payload = recv_conn.recv()
    process.join(10)

    if process.exitcode not in (0, None):
        raise AssertionError(f"Child process {target.__name__} exited with code {process.exitcode}")
    if not payload.get("ok"):
        raise AssertionError(f"Child process {target.__name__} failed: {payload.get('error')}")
    return payload


def test_cross_process_session_cookie_visibility():
    """Session cookie from process A authenticates process B with same secret key."""
    password = "testpass123"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    shared_secret_key = hashlib.sha256(b"shared-local-session-secret").hexdigest()

    db_a = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_b = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_a.close()
    db_b.close()

    try:
        env_a = _build_env(db_a.name, password_hash, shared_secret_key)
        env_b = _build_env(db_b.name, password_hash, shared_secret_key)

        login_payload = _run_child(_login_in_child, env_a, password)
        assert login_payload["status_code"] == 302
        assert login_payload["session_cookie"]

        validate_payload = _run_child(
            _validate_in_child,
            env_b,
            login_payload["session_cookie"],
        )
        assert validate_payload["unauth_status"] == 401
        assert validate_payload["auth_status"] == 200
        assert validate_payload["auth_payload"].get("status") == "ok"
        assert "keys" in validate_payload["auth_payload"]
    finally:
        os.unlink(db_a.name)
        os.unlink(db_b.name)
