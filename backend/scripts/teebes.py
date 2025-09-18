#!/usr/bin/env python3
"""
Django Model Manipulation Script Template

This template provides a foundation for creating scripts that interact with Django models.
Copy this file and modify it for your specific needs.

Usage:
    python backend/scripts/template.py
    # or from the backend directory:
    python scripts/template.py
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path so we can import Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Now you can import your Django models and other modules
from django.contrib.auth import get_user_model

User = get_user_model()


def main():
    pass

if __name__ == '__main__':
    # Parse command line arguments if needed
    import argparse

    parser = argparse.ArgumentParser(description='Django model manipulation script')
    args = parser.parse_args()

    try:
        main()

    except KeyboardInterrupt:
        print("\n🛑 Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)