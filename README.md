# Building Finder

A simple web application that helps you find buildings within a specified radius of any address. Built with FastAPI and OpenStreetMap data.

## Features
- Search buildings near any address
- Adjustable search radius (50-200 meters)
- Shows building details:
  - Address
  - Distance from search point
  - Building type
  - Coordinates

## Installation

### Requirements
- Python 3.7+
- pip (Python package installer)

### Steps

1. Clone the repository:
```bash
git clone [repository-url]
cd building-finder
```

2. Install dependencies:

#### Unix/MacOS:
```bash
# Make script executable
chmod +x install.sh

# Run installation script
./install.sh
```

The script will:
- Create a virtual environment (.venv)
- Activate the virtual environment
- Install all required dependencies

#### Windows:
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\activate

# Install dependencies
install.bat
```

## Running the Application

1. Activate virtual environment (if not already activated):
```bash
# Unix/MacOS:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

2. Start the server:
```bash
uvicorn backend.main:app --reload
```

3. Open your web browser and go to:
```
http://localhost:8000
```

## Project Structure
```
building-finder/
├── backend/
│   └── main.py         # FastAPI application and API endpoints
├── frontend/
│   ├── static/         # Static files
│   └── templates/      # HTML templates
│       ├── base.html   # Base template
│       └── home.html   # Main page template
├── install.sh          # Unix installation script
├── install.bat         # Windows installation script
├── requirements.txt    # Python dependencies
└── constraints.txt     # Pip installation constraints
```

## API Endpoints

### GET /api/nearby-houses
Finds buildings near a specified address within a given radius.

Parameters:
- `address`: Street address to search near (required)
- `radius`: Search radius in meters (optional, default: 100)

Example request:
```
GET /api/nearby-houses?address=123 Main St, New York&radius=150
```

Example response:
```json
[
    {
        "id": "123456789",
        "address": "123 Main Street",
        "type": "residential",
        "distance": "45m away",
        "lat": 51.5074,
        "lng": -0.1278
    },
    {
        "id": "987654321",
        "address": "125 Main Street",
        "type": "commercial",
        "distance": "80m away",
        "lat": 51.5075,
        "lng": -0.1279
    }
]
```

## Technologies Used
- FastAPI (backend framework)
- OpenStreetMap's Overpass API (building data)
- Nominatim (geocoding service)
- Tailwind CSS (styling)

## Limitations
- Depends on OpenStreetMap data completeness
- Subject to API rate limits
- Building addresses may not always be available
- Search radius limited to 200 meters maximum