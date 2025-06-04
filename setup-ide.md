# IDE Setup Guide

## Configure Cursor/VS Code Python Interpreter

### Quick Setup Steps:

1. **Open Command Palette:**
   - Press `Cmd+Shift+P` (macOS) or `Ctrl+Shift+P` (Windows/Linux)

2. **Search for Python interpreter:**
   - Type: `Python: Select Interpreter`

3. **Choose your virtual environment:**
   - Select: `/Users/teebes/code/drawtwo/venv/bin/python`
   - Or browse and navigate to the `venv/bin/python` file in this project

### Verify Setup:

After selecting the interpreter, you should see:
- ✅ No more red squiggly lines under `django.contrib` imports
- ✅ IntelliSense working for Django classes and functions
- ✅ Jump to definition working (Cmd+Click or F12)
- ✅ Auto-completion for Django models, views, etc.

### Troubleshooting:

If you still see import errors:
1. Make sure the virtual environment is activated in the terminal
2. Restart Cursor/VS Code
3. Check that you selected the correct Python interpreter path
4. Try running: `source venv/bin/activate && python -c "import django; print('Django 5.1.10 working!')"`

### Files Created:

- `venv/` - Local virtual environment (gitignored)
- `requirements-dev.txt` - Development dependencies
- `.vscode/settings.json` - VS Code configuration
- Updated `.gitignore` and `README.md`

### What's Updated:

- ✅ **Django 5.1.10** - Latest stable Django version
- ✅ **Django REST Framework 3.15.2** - Latest DRF version
- ✅ **Updated dependencies** - All packages upgraded to latest compatible versions
- ✅ **Better type hints** - Django 5.1 stubs for improved IntelliSense

Your Docker setup remains unchanged - the app still runs in containers!