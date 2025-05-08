#!/bin/bash
set -e

# Create a virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate the virtual environment
source venv/bin/activate

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing requirements..."
    pip install -r requirements.txt
else
    echo "Creating requirements.txt and installing dependencies..."
    cat > requirements.txt << EOF
Django==4.2.7
neo4j==5.13.0
pandas==2.1.1
matplotlib==3.8.0
networkx==3.2
plotly==5.18.0
EOF
    pip install -r requirements.txt
fi

# Check if Django project exists
if [ ! -d "mrgraph" ]; then
    echo "Setting up Django project..."
    django-admin startproject mrgraph .
    
    # Create the app
    python manage.py startapp graphapp
    
    # Update settings.py to include our app
    sed -i '' "s/INSTALLED_APPS = \[/INSTALLED_APPS = \[\n    'graphapp',/" mrgraph/settings.py
    
    # Create necessary directories
    mkdir -p templates/graphapp
    mkdir -p static/graphapp/css
    mkdir -p static/graphapp/js
fi

# Run migrations
echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

# Run the server
echo "Starting server..."
python manage.py runserver 