#!/bin/bash
set -e

# Function to check if Neo4j is running
check_neo4j_running() {
    echo "Checking if Neo4j is running..."
    
    # Check if netcat is installed
    if ! command -v nc &> /dev/null; then
        echo "Warning: 'nc' (netcat) command not found. Installing alternative check method..."
        # Try using lsof instead
        if command -v lsof &> /dev/null; then
            if lsof -i:7474 -sTCP:LISTEN &>/dev/null || lsof -i:7687 -sTCP:LISTEN &>/dev/null; then
                echo "Neo4j is running."
                return 0
            else
                echo "ERROR: Neo4j is not running!"
                echo "Please start Neo4j before running the Django server."
                echo "You can start Neo4j using one of these methods:"
                echo "  - If using Neo4j Desktop: Open the app and start your database"
                echo "  - If installed with Homebrew: brew services start neo4j"
                echo "  - If installed manually: <path-to-neo4j>/bin/neo4j start"
                return 1
            fi
        else
            echo "Warning: Both 'nc' and 'lsof' commands not found. Skipping Neo4j check."
            return 0  # Continue anyway since we can't check
        fi
    else
        # Use netcat to check
        if nc -z localhost 7474 &>/dev/null || nc -z localhost 7687 &>/dev/null; then
            echo "Neo4j is running."
            return 0
        else
            echo "ERROR: Neo4j is not running!"
            echo "Please start Neo4j before running the Django server."
            echo "You can start Neo4j using one of these methods:"
            echo "  - If using Neo4j Desktop: Open the app and start your database"
            echo "  - If installed with Homebrew: brew services start neo4j"
            echo "  - If installed manually: <path-to-neo4j>/bin/neo4j start"
            return 1
        fi
    fi
}

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
    python3 manage.py startapp graphapp
    
    # Update settings.py to include our app
    sed -i '' "s/INSTALLED_APPS = \[/INSTALLED_APPS = \[\n    'graphapp',/" mrgraph/settings.py
    
    # Create necessary directories
    mkdir -p templates/graphapp
    mkdir -p static/graphapp/css
    mkdir -p static/graphapp/js
fi

# Run migrations
echo "Running migrations..."
python3 manage.py makemigrations
python3 manage.py migrate

# Check if Neo4j is running before starting Django
if check_neo4j_running; then
    # Run the server
    echo "Starting server..."
    python3 manage.py runserver 
else
    exit 1
fi 