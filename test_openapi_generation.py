#!/usr/bin/env python3
"""
Test script to verify OpenAPI schema generation works.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Importing FastAPI app...")
    from app.main import app

    print("✅ App imported successfully")

    print("\nTesting OpenAPI schema generation...")

    # Try to get the schema
    try:
        schema = app.openapi()
        print("✅ OpenAPI schema generated successfully")
        print(f"📊 Title: {schema.get('info', {}).get('title')}")
        print(f"📊 Version: {schema.get('info', {}).get('version')}")
        print(f"📊 Paths: {len(schema.get('paths', {}))}")

        # Check if security schemes are present
        security_schemes = schema.get("components", {}).get("securitySchemes", {})
        print(f"🔒 Security schemes: {list(security_schemes.keys())}")

    except Exception as e:
        print(f"❌ Error generating OpenAPI schema: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    print("\n✅ All tests passed!")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
