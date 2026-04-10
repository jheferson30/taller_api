#!/usr/bin/env python3
"""
Script to export OpenAPI schema to openapi.json file.

Usage:
    python export_openapi.py
"""

import json
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app


def export_openapi_schema():
    """Export OpenAPI schema to openapi.json file."""
    try:
        # Get OpenAPI schema from FastAPI app
        openapi_schema = app.openapi()

        # Write to file with pretty formatting
        output_file = Path(__file__).parent / "openapi.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(openapi_schema, f, indent=2, ensure_ascii=False)

        print(f"✅ OpenAPI schema exported successfully to: {output_file}")
        print(f"📊 Schema contains {len(openapi_schema.get('paths', {}))} endpoints")

        # Print summary
        paths = openapi_schema.get("paths", {})
        methods_count = {}
        for _path, methods in paths.items():
            for method in methods:
                if method in ["get", "post", "put", "delete", "patch"]:
                    methods_count[method.upper()] = methods_count.get(method.upper(), 0) + 1

        print("\n📈 Endpoints by method:")
        for method, count in sorted(methods_count.items()):
            print(f"  {method}: {count}")

        return True

    except Exception as e:
        print(f"❌ Error exporting OpenAPI schema: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = export_openapi_schema()
    sys.exit(0 if success else 1)
