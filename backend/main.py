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
    # Overpass QL query to find buildings within radius
    print(f"Searching for buildings around ({latitude}, {longitude}) with radius {radius}m")
    query = f"""
    [out:json][timeout:25];
    (
      // Find all buildings in area
      way(around:{radius},{latitude},{longitude})["building"];
      relation(around:{radius},{latitude},{longitude})["building"];
      // Also find amenities that might be buildings
      way(around:{radius},{latitude},{longitude})["amenity"];
      // Find places with addresses even if not tagged as buildings
      way(around:{radius},{latitude},{longitude})["addr:housenumber"];
      way(around:{radius},{latitude},{longitude})["addr:street"];
    );
    out body center qt;
    """
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OVERPASS_API_URL, data={"data": query}) as response:
                if response.status != 200:
                    logger.error(f"Overpass API error: {response.status}")
                    return []
                data = await response.json()
                print(data)
                print(f"Found {len(data.get('elements', []))} elements in response")
                buildings = []
                
                for element in data.get("elements", []):
                    if "center" in element:
                        # Get all tags for debugging
                        tags = element.get("tags", {})
                        print(f"Processing building with tags: {tags}")
                        
                        building = {
                            "id": element["id"],
                            "lat": element["center"]["lat"],
                            "lng": element["center"]["lon"],
                            "address": "",
                            "type": tags.get("building", "building")
                        }
                        
                        # Try different address formats
                        if "addr:housenumber" in tags and "addr:street" in tags:
                            building["address"] = f"{tags['addr:street']} {tags['addr:housenumber']}"
                        elif "addr:full" in tags:
                            building["address"] = tags["addr:full"]
                        elif "name" in tags:
                            building["address"] = tags["name"]
                        
                        # If no address is found, create a generic one
                        if not building["address"].strip():
                            building["address"] = f"Building at ({building['lat']:.6f}, {building['lng']:.6f})"
                        
                        buildings.append(building)
                
                print(f"Processed {len(buildings)} buildings")
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
        # print(f"Received request - Address: {address}, Radius: {radius}")  # Debug print
        
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
                "address_found": False,
                "details": geocode_result  # Include full details for debugging
            }
            
        latitude, longitude = geocode_result["coords"]
        print(f"Found coordinates: {latitude}, {longitude}")  # Debug print
        
        buildings = await fetch_nearby_buildings(latitude, longitude, radius)
        print(f"Found {len(buildings)} buildings")  # Debug print
        
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
            "error": str(e),
            "address_found": False,
            "details": {"error_type": type(e).__name__}
        }

async def get_coordinates_from_address(address: str) -> Dict:
    """Convert address to coordinates using Nominatim"""
    url = "https://nominatim.openstreetmap.org/search"
    
    # Format address for better geocoding results
    formatted_address = address.strip()
    
    params = {
        "q": formatted_address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "accept-language": "en"
    }
    
    headers = {
        "User-Agent": "AddressLookupApp/1.0"  # Changed to a simple user agent
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:  # Added timeout
            # print(f"Sending request to Nominatim: {url} with params: {params}")  # Debug print
            response = await client.get(url, params=params, headers=headers)
            # print(f"Nominatim response status: {response.status_code}")  # Debug print
            
            response.raise_for_status()
            data = response.json()
            # print(f"Nominatim response data: {data}")  # Debug print
            
            if data:
                return {
                    "success": True,
                    "coords": (float(data[0]['lat']), float(data[0]['lon'])),
                    "display_name": data[0].get('display_name', '')
                }
            
            # If no results found with full address, try simplified version
            simplified_address = address.split(',')[0].strip()
            if simplified_address != formatted_address:
                params["q"] = simplified_address
                print(f"Trying simplified address: {simplified_address}")  # Debug print
                
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
            
            return {
                "success": False,
                "error": "Could not find the specified address. Please check the spelling or try a different address.",
                "status_code": 404
            }
                
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")  # Debug print
        return {
            "success": False,
            "error": f"Geocoding service error (HTTP {e.response.status_code})",
            "status_code": e.response.status_code
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Geocoding service timeout. Please try again.",
            "status_code": 408
        }
    except Exception as e:
        print(f"Unexpected error: {e}")  # Debug print
        return {
            "success": False,
            "error": f"Error processing address: {str(e)}",
            "status_code": 500
        }