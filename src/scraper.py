import requests
from src.config import Config
import json
import time
import random
import re
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Yad2Scraper:
    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        self._setup_session()
        logger.info("Yad2Scraper initialized with configuration")

    def _setup_session(self):
        """Setup the session with realistic browser headers."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.yad2.co.il/realestate/rent',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'DNT': '1'
        })
        logger.debug("Session headers configured")

    def _get_search_params(self):
        """Get the search parameters."""
        return {
            'maxPrice': 13000,
            'minRooms': 3,
            'maxRooms': 4,
            'property': 1,  # 1 for apartments
            'parking': 1,
            'shelter': 1,
            'zoom': 15,
            'topArea': 2,
            'area': 1,
            'city': 5000,  # Tel Aviv
            'neighborhood': 204,  # Start with New North (but should also bring Old North, Kikar HaMedina)
            'bBox': '32.086500,34.775423,32.097854,34.792422',
            'page': 1,
            'limit': 50  # Increase the number of results per page
        }

    def _simulate_browser_behavior(self):
        """Simulate realistic browser behavior."""
        logger.debug("Simulating browser behavior")
        # Add a small random delay
        time.sleep(random.uniform(1, 3))
        
        # Visit the homepage first
        logger.debug("Visiting homepage")
        self.session.get(f"{self.config.API_URL}/")
        time.sleep(random.uniform(0.5, 1.5))
        
        # Visit the real estate section
        logger.debug("Visiting real estate section")
        self.session.get(f"{self.config.API_URL}/realestate")
        time.sleep(random.uniform(0.5, 1.5))

    def search_listings(self):
        """Search for listings by scraping the HTML page directly."""
        try:
            # Simulate browser behavior
            self._simulate_browser_behavior()
            
            all_listings = []
            # Correct neighborhood names for North Tel Aviv
            neighborhoods = [
                "הצפון החדש - צפון",
                "הצפון החדש - כיכר המדינה",
                "הצפון הישן - צפון"
            ]
            
            for neighborhood_name in neighborhoods:
                logger.info(f"Searching in {neighborhood_name}...")
                
                # Construct the search URL with parameters
                search_url = f"{self.config.API_URL}/realestate/rent"
                params = {
                    "city": 5000,
                    "rooms": "3-4",
                    "price": "0-13000",
                    "property": 1,
                    "parking": 1,
                    "shelter": 1,
                    "page": 1,
                    "limit": 50,
                    "component-type": "rent",
                    "spot": "rent",
                    "location": "tel-aviv",
                    "opened-from": "today",
                    "text": neighborhood_name  # Use neighborhood name in search
                }
                
                logger.debug(f"Making request to: {search_url}")
                logger.debug(f"With params: {json.dumps(params, indent=2)}")
                
                try:
                    response = self.session.get(
                        search_url,
                        params=params,
                        headers={
                            **self.session.headers,
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
                            'Cache-Control': 'no-cache',
                            'Pragma': 'no-cache',
                            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                            'Sec-Ch-Ua-Mobile': '?0',
                            'Sec-Ch-Ua-Platform': '"macOS"',
                            'Sec-Fetch-Dest': 'document',
                            'Sec-Fetch-Mode': 'navigate',
                            'Sec-Fetch-Site': 'none',
                            'Sec-Fetch-User': '?1',
                            'Upgrade-Insecure-Requests': '1'
                        },
                        timeout=30  # Add timeout
                    )
                    
                    logger.info(f"Response status code: {response.status_code}")
                    
                    if response.status_code == 200:
                        html_content = response.text
                        
                        # Save HTML content for debugging
                        debug_file = f"debug_html_{neighborhood_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                        with open(os.path.join(get_data_dir(), debug_file), 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        logger.debug(f"Saved HTML content to {debug_file}")
                        
                        # Look for various possible data patterns
                        patterns = [
                            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
                            r'window\.__APOLLO_STATE__\s*=\s*({.*?});',
                            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                            r'<script type="application/json" id="__NEXT_DATA__">(.*?)</script>'
                        ]
                        
                        data_found = False
                        for pattern in patterns:
                            matches = re.findall(pattern, html_content, re.DOTALL)
                            if matches:
                                logger.debug(f"Found data with pattern: {pattern}")
                                try:
                                    # For patterns that include the script tag, we need to parse the content
                                    if 'script' in pattern:
                                        data = json.loads(matches[0])
                                    else:
                                        data = json.loads(matches[0])
                                    logger.debug("Successfully parsed JSON data")
                                    
                                    # Save JSON data for debugging
                                    debug_json = f"debug_json_{neighborhood_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                                    with open(os.path.join(get_data_dir(), debug_json), 'w', encoding='utf-8') as f:
                                        json.dump(data, f, ensure_ascii=False, indent=2)
                                    logger.debug(f"Saved JSON data to {debug_json}")
                                    
                                    # Parse the listings from this neighborhood
                                    neighborhood_listings = self.parse_listings(data)
                                    
                                    # Filter listings to only include those from the current neighborhood
                                    filtered_listings = [
                                        listing for listing in neighborhood_listings
                                        if listing.get('address', {}).get('neighborhood') == neighborhood_name
                                    ]
                                    
                                    logger.info(f"Found {len(filtered_listings)} listings in {neighborhood_name}")
                                    all_listings.extend(filtered_listings)
                                    data_found = True
                                    break
                                except json.JSONDecodeError as e:
                                    logger.error(f"Error parsing JSON: {e}")
                                    continue
                                except Exception as e:
                                    logger.error(f"Error parsing listings for {neighborhood_name}: {str(e)}")
                                    continue
                        
                        if not data_found:
                            logger.warning(f"Could not find any known data patterns in HTML for {neighborhood_name}")
                            logger.debug("Available patterns in HTML:")
                            for pattern in patterns:
                                matches = re.findall(pattern, html_content, re.DOTALL)
                                logger.debug(f"Pattern {pattern}: {len(matches)} matches")
                    else:
                        logger.error(f"Error: Got status code {response.status_code}")
                        logger.debug(f"Response headers: {response.headers}")
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error for {neighborhood_name}: {str(e)}")
                    continue
                
                # Add a small delay between requests
                time.sleep(random.uniform(2, 4))  # Increased delay
            
            logger.info(f"Total listings found across all neighborhoods: {len(all_listings)}")
            
            # Verify all listings are from the correct neighborhoods
            for listing in all_listings:
                neighborhood = listing.get('address', {}).get('neighborhood', '')
                if neighborhood not in neighborhoods:
                    logger.warning(f"Found listing from unexpected neighborhood: {neighborhood}")
            
            return all_listings
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}", exc_info=True)
            return []

    def parse_listings(self, data):
        """Parse the listings from the response data."""
        try:
            # If data is already a list of listings, return it
            if isinstance(data, list):
                return data
            
            # Find the feed data in the Next.js initial state
            feed_data = None
            for query in data['props']['pageProps']['dehydratedState']['queries']:
                if 'data' in query['state'] and isinstance(query['state']['data'], dict):
                    if 'private' in query['state']['data'] or 'agency' in query['state']['data']:
                        feed_data = query['state']['data']
                        break
            
            if not feed_data:
                logger.warning("No feed data found in the response")
                return []
            
            listings = []
            
            # Process private listings
            if 'private' in feed_data:
                for listing in feed_data['private']:
                    try:
                        # Check if the address contains any excluded street
                        street_name = listing.get('address', {}).get('street', {}).get('text', '')
                        if hasattr(Config, 'EXCLUDED_STREETS') and any(excluded in street_name for excluded in Config.EXCLUDED_STREETS):
                            logger.debug(f"Skipping listing in excluded street: {street_name}")
                            continue
                        
                        parsed = {
                            'id': listing.get('orderId'),
                            'type': 'private',
                            'title': f"{listing.get('additionalDetails', {}).get('property', {}).get('text', '')} - {listing.get('address', {}).get('street', {}).get('text', '')} {listing.get('address', {}).get('house', {}).get('number', '')}",
                            'price': listing.get('price'),
                            'address': {
                                'street': listing.get('address', {}).get('street', {}).get('text', ''),
                                'number': listing.get('address', {}).get('house', {}).get('number', ''),
                                'floor': listing.get('address', {}).get('house', {}).get('floor', ''),
                                'neighborhood': listing.get('address', {}).get('neighborhood', {}).get('text', ''),
                                'city': listing.get('address', {}).get('city', {}).get('text', '')
                            },
                            'details': {
                                'rooms': listing.get('additionalDetails', {}).get('roomsCount'),
                                'square_meters': listing.get('additionalDetails', {}).get('squareMeter'),
                                'square_meters_build': listing.get('metaData', {}).get('squareMeterBuild', listing.get('additionalDetails', {}).get('squareMeter')),
                                'condition': listing.get('additionalDetails', {}).get('propertyCondition', {}).get('id')
                            },
                            'images': listing.get('metaData', {}).get('images', []),
                            'cover_image': listing.get('metaData', {}).get('coverImage', ''),
                            'link': f"https://www.yad2.co.il/item/{listing.get('token', '')}"
                        }
                        # Clean up None values
                        parsed = {k: v for k, v in parsed.items() if v is not None}
                        listings.append(parsed)
                    except Exception as e:
                        logger.error(f"Error parsing private listing: {str(e)}")
                        continue
            
            # Process agency listings
            if 'agency' in feed_data:
                for listing in feed_data['agency']:
                    try:
                        # Check if the address contains any excluded street
                        street_name = listing.get('address', {}).get('street', {}).get('text', '')
                        if hasattr(Config, 'EXCLUDED_STREETS') and any(excluded in street_name for excluded in Config.EXCLUDED_STREETS):
                            logger.debug(f"Skipping listing in excluded street: {street_name}")
                            continue
                        
                        parsed = {
                            'id': listing.get('orderId'),
                            'type': 'agency',
                            'title': f"{listing.get('additionalDetails', {}).get('property', {}).get('text', '')} - {listing.get('address', {}).get('street', {}).get('text', '')} {listing.get('address', {}).get('house', {}).get('number', '')}",
                            'price': listing.get('price'),
                            'address': {
                                'street': listing.get('address', {}).get('street', {}).get('text', ''),
                                'number': listing.get('address', {}).get('house', {}).get('number', ''),
                                'floor': listing.get('address', {}).get('house', {}).get('floor', ''),
                                'neighborhood': listing.get('address', {}).get('neighborhood', {}).get('text', ''),
                                'city': listing.get('address', {}).get('city', {}).get('text', '')
                            },
                            'details': {
                                'rooms': listing.get('additionalDetails', {}).get('roomsCount'),
                                'square_meters': listing.get('additionalDetails', {}).get('squareMeter'),
                                'square_meters_build': listing.get('metaData', {}).get('squareMeterBuild', listing.get('additionalDetails', {}).get('squareMeter')),
                                'condition': listing.get('additionalDetails', {}).get('propertyCondition', {}).get('id')
                            },
                            'agency': listing.get('customer', {}).get('agencyName', ''),
                            'images': listing.get('metaData', {}).get('images', []),
                            'cover_image': listing.get('metaData', {}).get('coverImage', ''),
                            'link': f"https://www.yad2.co.il/item/{listing.get('token', '')}"
                        }
                        
                        # Add tags if present
                        if 'tags' in listing:
                            parsed['tags'] = [tag.get('name', '') for tag in listing['tags'] if tag.get('name')]
                        
                        # Clean up None values
                        parsed = {k: v for k, v in parsed.items() if v is not None}
                        listings.append(parsed)
                    except Exception as e:
                        logger.error(f"Error parsing agency listing: {str(e)}")
                        continue
            
            return listings
            
        except Exception as e:
            logger.error(f"Error parsing listings: {str(e)}", exc_info=True)
            logger.debug("Raw data structure:")
            logger.debug(json.dumps(data, indent=2))
            return [] 