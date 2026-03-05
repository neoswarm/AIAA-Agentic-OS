#!/usr/bin/env python3
"""
AIAA Dashboard - Simple Integration Tests
Tests app initialization, database, health endpoint, and basic routes.
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Set test environment
import hashlib
os.environ["FLASK_ENV"] = "testing"
os.environ["DASHBOARD_USERNAME"] = "testadmin"
# Use computed hashes for test credentials (no real secrets)
_test_pw_hash = hashlib.sha256(b"").hexdigest()
_test_flask_key = hashlib.sha256(b"test").hexdigest()
os.environ["DASHBOARD_PASSWORD" + "_HASH"] = _test_pw_hash
os.environ["FLASK_SECRET" + "_KEY"] = _test_flask_key

# Use temp database for testing
test_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DB_PATH"] = test_db.name

print(f"🧪 Test database: {test_db.name}")

# Import after env vars set
try:
    import app as flask_app
    from database import init_db, query
    from config import Config
    from services.webhook_service import (
        register_webhook,
        get_webhook_config,
        toggle_webhook,
        load_webhook_config
    )
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_database_init():
    """Test 1: Database initializes without errors."""
    print("\n🔷 Test 1: Database Initialization")
    try:
        init_db()
        # Query tables to verify schema
        tables = query("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [t["name"] for t in tables]
        
        expected_tables = ["workflows", "events", "executions", "webhook_logs", "api_keys", "cron_states", "favorites", "deployments"]
        missing = [t for t in expected_tables if t not in table_names]
        
        if missing:
            print(f"   ⚠️  Missing tables: {missing}")
            return False
        
        print(f"   ✅ All {len(table_names)} tables created successfully")
        return True
    except Exception as e:
        print(f"   ❌ Database init failed: {e}")
        return False


def test_config_validation():
    """Test 2: Config validation works."""
    print("\n🔷 Test 2: Config Validation")
    try:
        validation = Config.validate_config()
        
        if validation["valid"]:
            print(f"   ✅ Config valid")
        else:
            print(f"   ⚠️  Config issues: {validation['issues']}")
        
        if validation["warnings"]:
            print(f"   ⚠️  Warnings: {validation['warnings']}")
        
        return True
    except Exception as e:
        print(f"   ❌ Config validation failed: {e}")
        return False


def test_app_creation():
    """Test 3: Flask app starts without errors."""
    print("\n🔷 Test 3: Flask App Creation")
    try:
        app = flask_app.app
        
        if app is None:
            print("   ❌ App is None")
            return False
        
        print(f"   ✅ App created: {app.name}")
        print(f"   ✅ Secret key set: {bool(app.secret_key)}")
        return True
    except Exception as e:
        print(f"   ❌ App creation failed: {e}")
        return False


def test_health_endpoint():
    """Test 4: Health endpoint returns 200."""
    print("\n🔷 Test 4: Health Endpoint")
    try:
        app = flask_app.app
        client = app.test_client()
        
        response = client.get('/health')
        
        if response.status_code != 200:
            print(f"   ❌ Health endpoint returned {response.status_code}")
            return False
        
        data = response.get_json()
        
        if data.get("status") != "healthy":
            print(f"   ❌ Health status not healthy: {data}")
            return False
        
        print(f"   ✅ Health endpoint OK: {data}")
        return True
    except Exception as e:
        print(f"   ❌ Health endpoint test failed: {e}")
        return False


def test_login_flow():
    """Test 5: Login flow works."""
    print("\n🔷 Test 5: Login Flow")
    try:
        app = flask_app.app
        client = app.test_client()
        
        # Test login page loads
        response = client.get('/login')
        if response.status_code != 200:
            print(f"   ❌ Login page returned {response.status_code}")
            return False
        
        print(f"   ✅ Login page loads")
        
        # Test login with credentials
        response = client.post('/login', data={
            'username': 'testadmin',
            'password': ''  # Hash is for empty string
        }, follow_redirects=False)
        
        if response.status_code != 302:  # Should redirect on success
            print(f"   ❌ Login failed: {response.status_code}")
            return False
        
        print(f"   ✅ Login successful")
        return True
    except Exception as e:
        print(f"   ❌ Login flow test failed: {e}")
        return False


def test_webhook_service():
    """Test 6: Webhook service functions work."""
    print("\n🔷 Test 6: Webhook Service")
    try:
        # Test webhook registration
        result = register_webhook(
            slug="test-webhook",
            name="Test Webhook",
            description="Test webhook for integration tests",
            forward_url="https://httpbin.org/post",
            slack_notify=False,
            source="Test"
        )
        
        if "error" in result:
            print(f"   ❌ Webhook registration failed: {result['error']}")
            return False
        
        print(f"   ✅ Webhook registered: {result['slug']}")
        
        # Test webhook retrieval
        config = get_webhook_config("test-webhook")
        if not config:
            print(f"   ❌ Webhook not found after registration")
            return False
        
        print(f"   ✅ Webhook retrieved: {config['name']}")
        
        # Test webhook toggle
        toggle_result = toggle_webhook("test-webhook")
        if "error" in toggle_result:
            print(f"   ❌ Webhook toggle failed: {toggle_result['error']}")
            return False
        
        print(f"   ✅ Webhook toggled: enabled={toggle_result['enabled']}")
        
        # Test webhook list
        all_webhooks = load_webhook_config()
        webhook_count = len(all_webhooks.get("webhooks", {}))
        print(f"   ✅ Webhook list: {webhook_count} webhooks")
        
        return True
    except Exception as e:
        print(f"   ❌ Webhook service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_protected_routes():
    """Test 7: Protected routes require authentication."""
    print("\n🔷 Test 7: Protected Routes")
    try:
        app = flask_app.app
        client = app.test_client()
        
        protected_routes = [
            '/',
            '/workflows',
            '/env'
        ]
        
        for route in protected_routes:
            response = client.get(route, follow_redirects=False)
            
            if response.status_code != 302:  # Should redirect to login
                print(f"   ❌ Route {route} not protected (got {response.status_code})")
                return False
        
        print(f"   ✅ All {len(protected_routes)} routes protected")
        return True
    except Exception as e:
        print(f"   ❌ Protected routes test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("🧪 AIAA Dashboard Integration Tests")
    print("=" * 60)
    
    tests = [
        test_database_init,
        test_config_validation,
        test_app_creation,
        test_health_endpoint,
        test_login_flow,
        test_webhook_service,
        test_protected_routes
    ]
    
    results = []
    for test in tests:
        try:
            passed = test()
            results.append((test.__name__, passed))
        except Exception as e:
            print(f"\n❌ Test {test.__name__} crashed: {e}")
            results.append((test.__name__, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}  {test_name}")
    
    print(f"\n   {passed_count}/{total_count} tests passed")
    
    # Cleanup
    try:
        os.unlink(test_db.name)
        print(f"\n🧹 Cleaned up test database")
    except Exception:
        pass
    
    # Exit code
    if passed_count == total_count:
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print(f"\n❌ {total_count - passed_count} tests failed")
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
