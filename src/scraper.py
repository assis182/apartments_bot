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
        # More realistic browser headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Origin': 'https://www.yad2.co.il',
            'Referer': 'https://www.yad2.co.il/realestate/rent',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'X-Requested-With': 'XMLHttpRequest'
        })
        logger.debug("Session headers configured")

    def _simulate_browser_behavior(self):
        """Simulate realistic browser behavior."""
        logger.debug("Simulating browser behavior")
        
        try:
            # Add dynamic viewport and screen properties
            viewport_width = random.choice([1440, 1536, 1920])
            viewport_height = random.choice([900, 864, 1080])
            
            # Update headers with more realistic browser properties
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"macOS"',
                'Sec-Ch-Ua-Platform-Version': '10_15_7',
                'Sec-Ch-Width': str(viewport_width),
                'Sec-Ch-Viewport-Width': str(viewport_width),
                'Viewport-Width': str(viewport_width),
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Cache-Control': 'max-age=0',
            })

            # Visit the homepage first
            logger.debug("Visiting homepage")
            home_response = self.session.get(
                'https://www.yad2.co.il',
                headers={
                    **self.session.headers,
                    'Purpose': 'prefetch',
                }
            )
            time.sleep(random.uniform(2, 4))

            # Then visit the real estate section
            logger.debug("Visiting real estate section")
            realestate_response = self.session.get(
                'https://www.yad2.co.il/realestate/rent',
                headers={
                    **self.session.headers,
                    'Referer': 'https://www.yad2.co.il',
                }
            )
            time.sleep(random.uniform(2, 4))

            # Store cookies from both responses
            all_cookies = []
            for response in [home_response, realestate_response]:
                if 'Set-Cookie' in response.headers:
                    all_cookies.extend(response.headers.getall('Set-Cookie'))
            
            if all_cookies:
                self.session.headers.update({'Cookie': '; '.join(all_cookies)})
                logger.debug("Updated session cookies")

            # Get the CSRF token
            csrf_token = None
            for response in [home_response, realestate_response]:
                match = re.search(r'csrf-token"\s+content="([^"]+)"', response.text)
                if match:
                    csrf_token = match.group(1)
                    self.session.headers.update({'X-CSRF-TOKEN': csrf_token})
                    logger.debug(f"Found CSRF token: {csrf_token}")
                    break

            # Make a preliminary API request
            logger.debug("Making preliminary API request")
            self.session.get(
                'https://www.yad2.co.il/api/pre-load',
                headers={
                    **self.session.headers,
                    'Accept': 'application/json',
                    'Referer': 'https://www.yad2.co.il/realestate/rent',
                }
            )
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            logger.error(f"Error during browser simulation: {str(e)}", exc_info=True)

    def search_listings(self):
        """Search for listings using the JSON API."""
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
            
            # Maximum number of retries per neighborhood
            max_retries = 3 if is_container else 2
            
            # Simulate browser behavior
            self._simulate_browser_behavior()
            
            all_listings = []
            neighborhoods = [
                "הצפון החדש - צפון",
                "הצפון החדש - כיכר המדינה",
                "הצפון הישן - צפון"
            ]
            
            any_request_succeeded = False
            
            for neighborhood_name in neighborhoods:
                logger.info(f"Searching in {neighborhood_name}...")
                
                for retry in range(max_retries):
                    if retry > 0:
                        logger.info(f"Retry {retry} for {neighborhood_name}")
                        time.sleep(random.uniform(5, 8))
                        self.session = requests.Session()
                        self._setup_session()
                        self._simulate_browser_behavior()
                    
                    try:
                        # Use the search API endpoint
                        search_params = {
                            'category': 2,  # Real estate
                            'subCategory': 2,  # Rent
                            'city': 5000,  # Tel Aviv
                            'neighborhood': neighborhood_name,
                            'price': '0-13000',
                            'rooms': '3-4',
                            'parking': 1,
                            'shelter': 1,
                            'page': 1,
                            'limit': 50
                        }
                        
                        response = self.session.get(
                            f"{self.config.API_URL}/api/feed/get",
                            params=search_params,
                            headers={
                                **self.session.headers,
                                'Accept': 'application/json, text/plain, */*',
                                'Sec-Fetch-Site': 'same-origin',
                                'Sec-Fetch-Mode': 'cors',
                                'Sec-Fetch-Dest': 'empty'
                            },
                            timeout=30
                        )
                        
                        logger.info(f"Response status code: {response.status_code}")
                        logger.debug(f"Response headers: {dict(response.headers)}")
                        
                        if response.status_code == 200:
                            try:
                                # Log the first 500 characters of the response for debugging
                                response_text = response.text
                                logger.debug(f"Response preview: {response_text[:500]}")
                                
                                # Check for common anti-bot indicators
                                if "captcha" in response_text.lower() or "shield" in response_text.lower():
                                    logger.error("Anti-bot protection detected in response")
                                    if retry < max_retries - 1:
                                        logger.info("Waiting longer before retry...")
                                        time.sleep(random.uniform(10, 15))  # Increased wait time
                                        continue
                                
                                data = response.json()
                                
                                # Check if we got a valid response
                                if 'feed' in data and 'feed_items' in data['feed']:
                                    any_request_succeeded = True
                                    neighborhood_listings = self.parse_listings(data['feed'])
                                    
                                    # Filter listings to only include those from the current neighborhood
                                    filtered_listings = [
                                        listing for listing in neighborhood_listings
                                        if listing.get('address', {}).get('neighborhood') == neighborhood_name
                                    ]
                                    
                                    logger.info(f"Found {len(filtered_listings)} listings in {neighborhood_name}")
                                    all_listings.extend(filtered_listings)
                                    break  # Success - move to next neighborhood
                                else:
                                    logger.warning("Response doesn't contain expected feed data structure")
                                    if retry < max_retries - 1:
                                        continue
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse JSON response: {str(e)}")
                                if retry < max_retries - 1:
                                    continue
                        else:
                            logger.error(f"Error: Got status code {response.status_code}")
                            if retry < max_retries - 1:
                                continue
                            
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Request error for {neighborhood_name}: {str(e)}")
                        if retry < max_retries - 1:
                            continue
                    
                    # Add delay between neighborhoods
                    if is_container:
                        time.sleep(random.uniform(4, 6))
                    else:
                        time.sleep(random.uniform(2, 4))
            
            if not any_request_succeeded:
                logger.error("All requests failed - keeping existing listings")
                return []
            
            logger.info(f"Total listings found across all neighborhoods: {len(all_listings)}")
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