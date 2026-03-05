#!/usr/bin/env python3
"""
Test script for deployment service.
Validates that the service can be imported and initialized.
"""
import os
import sys
from pathlib import Path

# Set PROJECT_ROOT environment variable
os.environ['PROJECT_ROOT'] = str(Path(__file__).parent.parent.parent.parent.resolve())

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_import():
    """Test that the service can be imported."""
    try:
        from services.deployment_service import DeploymentService, check_required_env_vars
        print("✅ Successfully imported DeploymentService")
        return True
    except ImportError as e:
        print(f"❌ Failed to import: {e}")
        return False

def test_initialization():
    """Test that the service can be initialized."""
    try:
        from services.deployment_service import DeploymentService
        
        # Test with dummy credentials
        service = DeploymentService(
            railway_api_token="test_token",
            project_id="test_project",
            environment_id="test_env"
        )
        
        print("✅ Successfully initialized DeploymentService")
        print(f"   - API URL: {service.api_url}")
        print(f"   - Timeout: {service.timeout}s")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return False

def test_check_required_env_vars():
    """Test the env var checking function."""
    try:
        from services.deployment_service import check_required_env_vars
        
        # Test with a known workflow
        missing = check_required_env_vars("cold-email-campaign")
        
        print("✅ Successfully checked required env vars")
        print(f"   - Workflow: cold-email-campaign")
        print(f"   - Missing vars: {missing if missing else 'None'}")
        return True
    except Exception as e:
        print(f"❌ Failed to check env vars: {e}")
        return False

def test_skill_finding():
    """Test that skills can be found."""
    try:
        from services.deployment_service import DeploymentService
        
        service = DeploymentService(
            railway_api_token="test_token",
            project_id="test_project",
            environment_id="test_env"
        )
        
        # Test finding a known skill
        skill_dir = service._find_skill("cold-email-campaign")
        
        print("✅ Successfully found skill")
        print(f"   - Skill dir: {skill_dir}")
        print(f"   - SKILL.md exists: {(skill_dir / 'SKILL.md').exists()}")
        print(f"   - .py files: {len(list(skill_dir.glob('*.py')))}")
        return True
    except Exception as e:
        print(f"❌ Failed to find skill: {e}")
        return False

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("DEPLOYMENT SERVICE TESTS")
    print("="*80 + "\n")
    
    tests = [
        ("Import", test_import),
        ("Initialization", test_initialization),
        ("Env Var Checking", test_check_required_env_vars),
        ("Skill Finding", test_skill_finding)
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n📋 Test: {name}")
        print("-" * 80)
        passed = test_func()
        results.append((name, passed))
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    print("=" * 80 + "\n")
    
    return passed_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
