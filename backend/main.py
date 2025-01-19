from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional
import logging
import aiohttp
import httpx
import math

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Overpass API endpoint
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

# Mount static files and templates
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

async def fetch_nearby_buildings(latitude: float, longitude: float, radius: float = 100) -> List[Dict]:
    """
    Fetch nearby buildings using OpenStreetMap's Overpass API
    radius is in meters
    """
    # Convert radius to miles (Overpass API uses miles)
    radius = radius / 1.60934
    
    # Overpass QL query to find buildings within radius
    query = f"""
    [out:json][timeout:25];
    (
      way["building"](around:{radius},{latitude},{longitude});
      relation["building"](around:{radius},{latitude},{longitude});
    );
    out center;
    """
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OVERPASS_API_URL, data={"data": query}) as response:
                if response.status != 200:
                    logger.error(f"Overpass API error: {response.status}")
                    return []
                
                data = await response.json()
                buildings = []
                
                for element in data.get("elements", []):
                    if "center" in element:
                        building = {
                            "id": element["id"],
                            "lat": element["center"]["lat"],
                            "lng": element["center"]["lon"],
                            "address": element.get("tags", {}).get("addr:street", "") + " " + 
                                     element.get("tags", {}).get("addr:housenumber", ""),
                            "type": element.get("tags", {}).get("building", "building")
                        }
                        
                        # If no address is found, create a generic one
                        # if not building["address"].strip():
                        #     building["address"] = f"Building at ({building['lat']:.6f}, {building['lng']:.6f})"
                        
                        if building["address"].strip():
                            buildings.append(building)
                
                return buildings
    
    except Exception as e:
        logger.error(f"Error fetching buildings: {str(e)}")
        return []

@app.get("/api/nearby-houses")
async def get_nearby_houses(
    address: str = None,
    radius: int = 100
):
    try:
        # Fetch nearby buildings from OpenStreetMap
        coords = await get_coordinates_from_address(address)
        if not coords:
            raise HTTPException(status_code=400, detail="Could not find coordinates for the provided address")
            
        latitude, longitude = coords
        buildings = await fetch_nearby_buildings(latitude, longitude, radius)
        
        # Add distance information and sort by distance
        for building in buildings:
            building["distance"] = round(
                math.sqrt(
                    (building["lat"] - latitude) ** 2 + 
                    (building["lng"] - longitude) ** 2
                ) * 111320,  # Convert degrees to meters (approximate)
                1
            )
        
        # Sort by distance
        buildings.sort(key=lambda x: x["distance"])
        
        # Filter buildings within the specified radius
        buildings = [b for b in buildings if b["distance"] <= radius]
        
        # Format the response
        nearby_houses = [{
            "id": b["id"],
            "address": b["address"],
            "type": b["type"],
            "distance": f"{b['distance']}m away",
            "lat": b["lat"],
            "lng": b["lng"]
        } for b in buildings]
        
        return nearby_houses
      
    except Exception as e:
        logger.error(f"Error in get_nearby_houses: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching nearby houses")

async def get_coordinates_from_address(address: str) -> Optional[tuple[float, float]]:
    """Convert address to coordinates using Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    
    headers = {
        "User-Agent": "YourApp/1.0"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            data = response.json()
            
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
            return None
    except Exception as e:
        logger.error(f"Error geocoding address: {e}")
        return None 