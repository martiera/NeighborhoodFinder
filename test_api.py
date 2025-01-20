import aiohttp
import asyncio
import json

async def test_geocoding(address: str):
    url = "https://nominatim.openstreetmap.org/search"
    
    # Try different parameter combinations
    test_params = [
        {
            "q": address,
            "format": "json",
            "limit": 1
        },
        {
            "street": "3620 meadowcroft ave",
            "city": "kalamazoo",
            "country": "usa",
            "format": "json",
            "limit": 1
        },
        {
            "q": "meadowcroft ave kalamazoo",
            "format": "json",
            "limit": 1
        }
    ]
    
    headers = {
        "User-Agent": "AddressTestScript/1.0"
    }
    
    async with aiohttp.ClientSession() as session:
        for i, params in enumerate(test_params, 1):
            print(f"\nTest {i}:")
            print(f"Parameters: {params}")
            
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    print(f"Status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        print(f"Response: {json.dumps(data, indent=2)}")
                    else:
                        print(f"Error response: {await response.text()}")
                    
                # Respect Nominatim's usage policy with a delay
                await asyncio.sleep(1)
                    
            except Exception as e:
                print(f"Error: {str(e)}")

# Run the test
address_to_test = "3620 meadowcroft ave, kalamazoo, usa"
asyncio.run(test_geocoding(address_to_test))