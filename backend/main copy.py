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
                        if not building["address"].strip():
                            building["address"] = f"Building at ({building['lat']:.6f}, {building['lng']:.6f})"
                        
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
        if not address:
            return {
                "error": "Please provide an address",
                "address_found": False
            }
            
        # Try to geocode the address
        geocode_result = await get_coordinates_from_address(address)
        if not geocode_result["success"]:
            return {
                "error": geocode_result["error"],
                "address_found": False
            }
            
        latitude, longitude = geocode_result["coords"]
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
        
        return {
            "address_found": True,
            "coords": geocode_result["coords"],
            "found_address": geocode_result["display_name"],
            "houses": nearby_houses
        }
      
    except Exception as e:
        logger.error(f"Error in get_nearby_houses: {str(e)}")
        return {
            "error": f"An error occurred while fetching nearby houses: {str(e)}",
            "address_found": False
        }

async def get_coordinates_from_address(address: str) -> Dict:
    """Convert address to coordinates using Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    
    # Format address for better geocoding results
    # formatted_address = address.replace('%20', '+').strip()
    formatted_address = address.replace(' ', '+').strip()
    
    params = {
        "q": formatted_address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "accept-language": "en"
    }
    
    headers = {
        "User-Agent": "YourApp/1.0 (your@email.com)"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            if data:
                return {
                    "success": True,
                    "coords": (float(data[0]['lat']), float(data[0]['lon'])),
                    "display_name": data[0].get('display_name', '')
                }
            else:
                # Try alternative search with less specific address
                simplified_address = address.split(',')[0].strip()
                params["q"] = simplified_address
                
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if data:
                    return {
                        "success": True,
                        "coords": (float(data[0]['lat']), float(data[0]['lon'])),
                        "display_name": data[0].get('display_name', ''),
                        "note": "Used simplified address"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Address not found",
                        "status_code": 404
                    }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"Geocoding service error: {e.response.status_code}",
            "status_code": e.response.status_code
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error processing address: {str(e)}",
            "status_code": 500
        }