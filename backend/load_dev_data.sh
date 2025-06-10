#!/bin/bash

# Development Data Loader Script
# This is a convenience script for common dev data operations

echo "🎮 DrawTwo Development Data Loader"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Please run this script from the backend directory"
    exit 1
fi

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: No virtual environment detected"
    echo "   Consider activating your virtual environment first"
    echo ""
fi

case "${1:-help}" in
    "fresh")
        echo "🔄 Loading fresh development data..."
        python manage.py load_dev_data --reset
        ;;
    "users")
        echo "👥 Loading user data only..."
        python manage.py load_dev_data --users
        ;;
    "cards")
        echo "🃏 Loading card data only..."
        python manage.py load_dev_data --cards
        ;;
    "all"|"")
        echo "📦 Loading all development data..."
        python manage.py load_dev_data
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  fresh    Clear existing dev data and reload everything"
        echo "  users    Load only user data"
        echo "  cards    Load only card data"
        echo "  all      Load all development data (default)"
        echo "  help     Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 fresh    # Complete reset"
        echo "  $0 users    # Add dev users"
        echo "  $0          # Load everything (safe to run multiple times)"
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac