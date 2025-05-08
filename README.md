# MrGraphy

A Django web application for creating, storing, and visualizing graph data.

## Features

- Create nodes with custom properties
- Define relationships between nodes
- Visualize the graph data using interactive plots
- Store data in both Django and Neo4j database

## Requirements

- Python 3.8 or higher
- Neo4j Graph Database (local or remote)
- Django 4.2+

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/MrGraphy.git
   cd MrGraphy
   ```

2. Run the setup script:
   ```
   bash setup.sh
   ```

   This script will:
   - Create a virtual environment
   - Install all required dependencies
   - Set up the Django project if it doesn't exist
   - Run migrations
   - Start the development server

3. Set up Neo4j:
   - Install Neo4j from [https://neo4j.com/download/](https://neo4j.com/download/)
   - Start your Neo4j server
   - Configure environment variables (optional):
     ```
     export NEO4J_URI="bolt://localhost:7687"
     export NEO4J_USER="neo4j"
     export NEO4J_PASSWORD="your-password"
     ```

4. Access the application:
   - Open your browser and navigate to `http://127.0.0.1:8000/`

## Usage

1. Add nodes via the "Add Node" page
2. Create relationships between nodes via the "Add Relationship" page
3. View your data on the "View Data" page
4. Click "Visualize" to see an interactive graph visualization

## Technologies Used

- Django
- Neo4j
- NetworkX
- Plotly
- Bootstrap 5

## License

MIT 