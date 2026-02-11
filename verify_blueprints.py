"""
Diagnostic script to verify blueprint registration
Run this from the project root: python verify_blueprints.py
"""
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("BLUEPRINT VERIFICATION SCRIPT")
print("=" * 60)

# Test 1: Check if capture.py exists and can be imported
print("\n1. Checking capture.py file...")
try:
    from app.routes.capture import capture_bp
    print("   ✓ capture_bp imported successfully")
    print(f"   Blueprint name: {capture_bp.name}")
    print(f"   Blueprint import name: {capture_bp.import_name}")
    
    # Check if the route is registered
    has_route = False
    for rule in capture_bp.url_map.iter_rules() if hasattr(capture_bp, 'url_map') else []:
        print(f"   Route: {rule.rule} -> {rule.endpoint}")
        has_route = True
    
    if not has_route:
        # Check deferred functions
        print(f"   Deferred functions: {len(capture_bp.deferred_functions)}")
        
except Exception as e:
    print(f"   ✗ Failed to import capture_bp: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Try to import all blueprints
print("\n2. Checking all blueprints...")
blueprints = [
    ('auth', 'app.routes.auth', 'auth_bp'),
    ('dashboard', 'app.routes.dashboard', 'dashboard_bp'),
    ('capture', 'app.routes.capture', 'capture_bp'),
    ('students', 'app.routes.students', 'students_bp'),
    ('subjects', 'app.routes.subjects', 'subjects_bp'),
    ('sessions', 'app.routes.sessions', 'sessions_bp'),
    ('attendance', 'app.routes.attendance', 'attendance_bp'),
    ('users', 'app.routes.users', 'users_bp'),
    ('api', 'app.routes.api', 'api_bp'),
]

for name, module_path, bp_name in blueprints:
    try:
        module = __import__(module_path, fromlist=[bp_name])
        bp = getattr(module, bp_name)
        print(f"   ✓ {name:12} -> {bp_name}")
    except Exception as e:
        print(f"   ✗ {name:12} -> ERROR: {e}")

# Test 3: Create app and check registered routes
print("\n3. Creating Flask app and checking routes...")
try:
    from app import create_app
    app = create_app()
    
    print(f"\n   Total routes registered: {len(list(app.url_map.iter_rules()))}")
    print("\n   Routes containing 'capture':")
    for rule in app.url_map.iter_rules():
        if 'capture' in rule.endpoint.lower() or 'capture' in rule.rule.lower():
            print(f"      {rule.endpoint:30} -> {rule.rule}")
    
    # Check if capture.capture_page exists
    if 'capture.capture_page' in [r.endpoint for r in app.url_map.iter_rules()]:
        print("\n   ✓ capture.capture_page endpoint is registered!")
    else:
        print("\n   ✗ capture.capture_page endpoint NOT FOUND")
        print("\n   All available endpoints:")
        for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.endpoint):
            print(f"      {rule.endpoint}")
            
except Exception as e:
    print(f"   ✗ Failed to create app: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)