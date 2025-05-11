import requests
from src.config import Config
import json
import time
import random
import re
import os
from datetime import datetime
import logging
from src.utils import get_data_dir, logger  # Updated import to use utils.py
import sys

stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

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
            # Log environment info
            is_container = os.getenv('CONTAINER_ENV') == 'true'
            logger.info(f"Running in container: {is_container}")
            logger.info(f"Python version: {sys.version}")
            logger.info(f"Requests version: {requests.__version__}")
            
            # Log current time in different formats
            now = datetime.now()
            logger.info(f"Current time: {now.isoformat()}")
            logger.info(f"Current timezone: {time.tzname}")
            
            # Simulate browser behavior
            self._simulate_browser_behavior()
            
            all_listings = []
            # Correct neighborhood names for North Tel Aviv
            neighborhoods = [
                "הצפון החדש - צפון",
                "הצפון החדש - כיכר המדינה",
                "הצפון הישן - צפון"
            ]
            
            any_request_succeeded = False  # Track if any request succeeded
            
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
                
                logger.info(f"Making request to: {search_url}")
                logger.info(f"With params: {json.dumps(params, indent=2)}")
                
                # Generate a more browser-like User-Agent
                user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                
                try:
                    # Log all request headers for debugging
                    full_headers = {
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
                        'Upgrade-Insecure-Requests': '1',
                        'User-Agent': user_agent
                    }
                    logger.debug("Request headers:")
                    for header, value in full_headers.items():
                        logger.debug(f"{header}: {value}")
                    
                    response = self.session.get(
                        search_url,
                        params=params,
                        headers=full_headers,
                        timeout=30  # Add timeout
                    )
                    
                    logger.info(f"Response status code: {response.status_code}")
                    logger.info("Response headers:")
                    for header, value in response.headers.items():
                        logger.info(f"{header}: {value}")
                    
                    if response.status_code == 200:
                        any_request_succeeded = True
                        html_content = response.text
                        
                        # Log HTML size and encoding
                        logger.info(f"Response encoding: {response.encoding}")
                        logger.info(f"HTML content length: {len(html_content)}")
                        logger.info(f"First 500 chars of HTML: {html_content[:500]}")
                        
                        # Check if we got a valid HTML response
                        if len(html_content) < 1000:  # Suspiciously small
                            logger.warning("Received suspiciously small HTML response")
                            logger.info(f"Full response content: {html_content}")
                            continue
                            
                        if not any(marker in html_content for marker in ['<html', '<body', '<head']):
                            logger.warning("Response doesn't appear to be HTML")
                            logger.info(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
                            logger.info(f"First 1000 chars: {html_content[:1000]}")
                            continue
                            
                        # Check for common anti-bot measures
                        if any(marker in html_content.lower() for marker in ['captcha', 'blocked', 'rate limit']):
                            logger.warning("Possible anti-bot measure detected")
                            logger.info(f"Response might indicate we're being blocked")
                            continue
                        
                        try:
                            # Save HTML content for debugging
                            debug_file = f"debug_html_{neighborhood_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                            debug_path = os.path.join(get_data_dir(), debug_file)
                            with open(debug_path, 'w', encoding='utf-8') as f:
                                f.write(html_content)
                            logger.info(f"Saved HTML content to {debug_file}")
                            
                            # Check file size after saving
                            file_size = os.path.getsize(debug_path)
                            logger.info(f"Saved HTML file size: {file_size} bytes")
                        except Exception as e:
                            logger.error(f"Failed to save debug HTML: {str(e)}")
                            # Continue processing even if debug save fails
                        
                        # Look for various possible data patterns
                        patterns = [
                            r'window\.__INITIAL_STATE__\s*=\s*({.*?});',
                            r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
                            r'window\.__APOLLO_STATE__\s*=\s*({.*?});',
                            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                            r'<script type="application/json" id="__NEXT_DATA__">(.*?)</script>',
                            # Add more specific patterns
                            r'<script>window\.__NEXT_DATA__\s*=\s*({.*?})</script>',
                            r'<script>window\.__INITIAL_DATA__\s*=\s*({.*?})</script>',
                            r'<script>window\.__FEED_DATA__\s*=\s*({.*?})</script>'
                        ]
                        
                        data_found = False
                        for pattern in patterns:
                            matches = re.findall(pattern, html_content, re.DOTALL)
                            if matches:
                                logger.debug(f"Found data with pattern: {pattern}")
                                logger.debug(f"First 200 chars of match: {matches[0][:200]}")
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
                                    # Log a sample of the problematic JSON
                                    sample = matches[0][:200] + "..." if len(matches[0]) > 200 else matches[0]
                                    logger.error(f"Problem JSON sample: {sample}")
                                    continue
                                except Exception as e:
                                    logger.error(f"Error parsing listings for {neighborhood_name}: {str(e)}")
                                    continue
                        
                        if not data_found:
                            logger.warning(f"Could not find any known data patterns in HTML for {neighborhood_name}")
                            # Log some debug info about the HTML content
                            logger.debug("HTML Content Stats:")
                            logger.debug(f"HTML length: {len(html_content)} chars")
                            logger.debug(f"Contains __NEXT_DATA__: {'__NEXT_DATA__' in html_content}")
                            logger.debug(f"Contains __INITIAL_STATE__: {'__INITIAL_STATE__' in html_content}")
                            logger.debug(f"Contains __PRELOADED_STATE__: {'__PRELOADED_STATE__' in html_content}")
                            # Log a sample of the HTML around potential data areas
                            for marker in ['__NEXT_DATA__', '__INITIAL_STATE__', '__PRELOADED_STATE__']:
                                idx = html_content.find(marker)
                                if idx != -1:
                                    start = max(0, idx - 100)
                                    end = min(len(html_content), idx + 100)
                                    logger.debug(f"Context around {marker}:")
                                    logger.debug(html_content[start:end])
                    else:
                        logger.error(f"Error: Got status code {response.status_code}")
                        logger.debug(f"Response headers: {response.headers}")
                        logger.debug(f"Response content: {response.text[:500]}...")  # Log first 500 chars
                    
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request error for {neighborhood_name}: {str(e)}")
                    continue
                
                # Add a longer delay between requests when running in cron
                if os.getenv('CONTAINER_ENV') == 'true':
                    time.sleep(random.uniform(4, 6))  # Longer delay in container
                else:
                    time.sleep(random.uniform(2, 4))  # Normal delay locally
            
            if not any_request_succeeded:
                logger.error("All requests failed - keeping existing listings")
                return []  # Return empty list to indicate failure but not remove existing listings
            
            logger.info(f"Total listings found across all neighborhoods: {len(all_listings)}")
            
            # Verify all listings are from the correct neighborhoods
            for listing in all_listings:
                neighborhood = listing.get('address', {}).get('neighborhood', '')
                if neighborhood not in neighborhoods:
                    logger.warning(f"Found listing from unexpected neighborhood: {neighborhood}")
            
            return all_listings
            
        except Exception as e:
            logger.error(f"Error during search: {str(e)}", exc_info=True)
            return []  # Return empty list to indicate failure but not remove existing listings

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