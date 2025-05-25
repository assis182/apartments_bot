import requests
from src.config import Config
import json
import time
import random
import re
import os
from datetime import datetime
import logging
from src.utils import get_data_dir, logger, setup_logging, load_tracked_listings, save_tracked_listings, is_excluded, is_street_excluded
import sys
import pickle
from pathlib import Path
import hashlib
from urllib.parse import urlencode
import socket
from requests.exceptions import RequestException, ProxyError

stdout_handler = logging.StreamHandler()
stdout_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

class Yad2Scraper:
    def __init__(self):
        self.config = Config()
        self.session = requests.Session()
        self.cookies_file = Path(get_data_dir()) / 'cookies.pkl'
        self.current_proxy_index = 0
        self.failed_attempts = 0
        self._load_cookies()
        self._setup_session()
        logger.info("Yad2Scraper initialized with configuration")

    def _get_next_proxy(self):
        """Rotate to the next proxy if proxy rotation is enabled."""
        if not self.config.USE_PROXY or not self.config.PROXY_URLS:
            return None
        
        if self.config.PROXY_ROTATION_ENABLED:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.config.PROXY_URLS)
        
        proxy_url = self.config.PROXY_URLS[self.current_proxy_index]
        logger.debug(f"Switching to proxy #{self.current_proxy_index + 1}")
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    def _get_browser_profile(self):
        """Get a consistent browser profile based on the current proxy."""
        profile_index = self.current_proxy_index % len(self.config.BROWSER_PROFILES)
        return self.config.BROWSER_PROFILES[profile_index]

    def _make_request(self, method, url, **kwargs):
        """Make a request with retry logic and proxy rotation."""
        max_retries = kwargs.pop('max_retries', self.config.MAX_RETRIES)
        
        for attempt in range(max_retries):
            try:
                # Update proxy if enabled
                if self.config.USE_PROXY:
                    kwargs['proxies'] = self._get_next_proxy()
                
                # Add timeout and allow redirects
                kwargs['timeout'] = self.config.REQUEST_TIMEOUT
                kwargs['allow_redirects'] = True
                
                # Make the request
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()  # Raise an error for bad status codes
                
                # Check if response is valid JSON for API endpoints
                if url.endswith('/getFeedIndex/realestate/rent'):
                    try:
                        response.json()
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON response (attempt {attempt + 1}/{max_retries})")
                        self.failed_attempts += 1
                        self._handle_request_failure()
                        continue
                
                # Reset failed attempts on success
                self.failed_attempts = 0
                return response
                
            except Exception as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    self._handle_request_failure()
                    continue
                raise

    def _handle_request_failure(self):
        """Handle request failure by rotating proxy and waiting."""
        if self.config.USE_PROXY:
            self._get_next_proxy()
        
        # Calculate delay based on failed attempts
        base_delay = self.config.RETRY_DELAY
        if self.config.PROGRESSIVE_DELAYS:
            base_delay *= (1 + self.failed_attempts)
        
        # Add some randomness to the delay
        delay = base_delay + random.uniform(1, 3)
        logger.info(f"Waiting {delay:.1f} seconds before retry...")
        time.sleep(delay)
        
        # Rotate browser profile
        self._setup_session()

    def _load_cookies(self):
        """Load cookies from file if they exist."""
        try:
            if self.cookies_file.exists():
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    if cookies:
                        # Only use cookies that are less than 24 hours old
                        current_time = time.time()
                        valid_cookies = {
                            name: cookie for name, cookie in cookies.items()
                            if 'expires' not in cookie or cookie['expires'] > current_time
                        }
                        if valid_cookies:
                            self.session.cookies.update(valid_cookies)
                            logger.info("Loaded valid cookies from file")
                        else:
                            logger.info("No valid cookies found in file")
        except Exception as e:
            logger.error(f"Error loading cookies: {str(e)}")

    def _save_cookies(self):
        """Save cookies to file."""
        try:
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.session.cookies.get_dict(), f)
            logger.info("Saved cookies to file")
        except Exception as e:
            logger.error(f"Error saving cookies: {str(e)}")

    def _setup_session(self):
        """Setup the session with realistic browser headers."""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,he;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })

    def _simulate_browser_behavior(self):
        """Simulate realistic browser behavior."""
        try:
            # Add some randomness to timing
            base_delay = random.uniform(1.5, 3)
            
            # Visit the homepage first
            logger.debug("Visiting homepage")
            home_response = self._make_request('GET', self.config.YAD2_API_URL)
            time.sleep(base_delay * random.uniform(1.0, 1.5))

            # Visit some random pages first
            random_pages = [
                '/realestate',
                '/realestate/forsale',
                '/realestate/commercial',
                '/vehicles',
                '/products'
            ]
            for page in random.sample(random_pages, 2):
                logger.debug(f"Visiting random page: {page}")
                self._make_request('GET', f"{self.config.YAD2_API_URL}{page}")
                time.sleep(base_delay * random.uniform(0.8, 1.2))

            # Then visit the real estate section
            logger.debug("Visiting real estate section")
            realestate_response = self._make_request(
                'GET',
                f"{self.config.YAD2_API_URL}/realestate/rent"
            )
            time.sleep(base_delay * random.uniform(1.2, 1.8))

            # Visit the apartments category with search params
            logger.debug("Visiting apartments category")
            search_params = {
                'propertyGroup': 'apartments',
                'city': '5000',  # Tel Aviv
                'property': '1'  # Apartment
            }
            apartments_response = self._make_request(
                'GET',
                f"{self.config.YAD2_API_URL}/realestate/rent",
                params=search_params
            )
            time.sleep(base_delay * random.uniform(1.5, 2.0))

            # Get the initial feed data
            logger.debug("Getting initial feed data")
            initial_feed_response = self._make_request(
                'GET',
                f"{self.config.YAD2_API_URL}/api/pre-load/getFeedIndex/realestate/rent",
                params={'propertyGroup': 'apartments', 'forceLdLoad': True}
            )
            time.sleep(base_delay * random.uniform(1.0, 1.5))

            # Extract and update CSRF token and other cookies
            for response in [home_response, realestate_response, apartments_response, initial_feed_response]:
                if response and response.status_code == 200 and 'text/html' in response.headers.get('Content-Type', ''):
                    match = re.search(r'csrf-token"\s+content="([^"]+)"', response.text)
                    if match:
                        csrf_token = match.group(1)
                        self.session.headers.update({
                            'X-CSRF-TOKEN': csrf_token,
                        })
                        logger.debug(f"Found CSRF token: {csrf_token}")
                        break

            # Save cookies for future use
            self._save_cookies()

        except Exception as e:
            logger.error(f"Error during browser simulation: {str(e)}")
            raise

    def search_listings(self):
        """Search for listings in all configured neighborhoods."""
        logger.info("Searching for listings...")
        
        # Force session refresh and browser simulation
        self.session = requests.Session()
        self._setup_session()
        self._simulate_browser_behavior()
        
        all_listings = []
        
        # Search in each configured neighborhood
        for neighborhood_id in self.config.NEIGHBORHOODS:
            logger.info(f"Searching in neighborhood ID {neighborhood_id}...")
            
            # Prepare search parameters
            params = {
                'topArea': self.config.TOP_AREA,
                'area': self.config.AREA,
                'city': self.config.CITY,
                'propertyGroup': 'apartments',
                'property': self.config.PROPERTY_TYPE,
                'rooms': self.config.ROOMS_RANGE,
                'price': self.config.PRICE_RANGE,
                'parking': self.config.PARKING,
                'shelter': self.config.SHELTER,
                'neighborhood': neighborhood_id,
                'forceLdLoad': 'true'
            }
            
            try:
                # Make the API request
                response = self._make_request(
                    'GET',
                    f"{self.config.YAD2_API_URL}/api/pre-load/getFeedIndex/realestate/rent",
                    params=params
                )
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Log raw response data for debugging
                        logger.debug(f"Raw response data: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        
                        if 'feed' in data and 'feed_items' in data['feed']:
                            items = data['feed']['feed_items']
                            # Log raw items data
                            logger.debug(f"Raw feed items: {json.dumps(items, indent=2, ensure_ascii=False)}")
                            
                            # Log the first item's structure
                            if items:
                                first_item = items[0]
                                logger.debug(f"First item type: {type(first_item)}")
                                if isinstance(first_item, list):
                                    logger.debug(f"First item length: {len(first_item)}")
                                    logger.debug(f"First item contents: {first_item}")
                                elif isinstance(first_item, dict):
                                    logger.debug(f"First item keys: {first_item.keys()}")
                            
                            neighborhood_listings = self.parse_listings(items, 'rent')
                            all_listings.extend(neighborhood_listings)
                            logger.info(f"Found {len(neighborhood_listings)} listings in neighborhood {neighborhood_id}")
                        else:
                            logger.warning(f"No feed items found in neighborhood {neighborhood_id}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse JSON response for neighborhood {neighborhood_id}: {str(e)}")
                else:
                    logger.error(f"Failed to get listings for neighborhood {neighborhood_id}. Status code: {response.status_code}")
                
                # Add a random delay between neighborhood searches
                delay = random.uniform(self.config.MIN_REQUEST_DELAY, self.config.MAX_REQUEST_DELAY)
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error searching neighborhood {neighborhood_id}: {str(e)}")
                continue
        
        return all_listings

    def parse_listings(self, items, listing_type):
        """Parse the listings from the response data."""
        try:
            listings = []
            total_items = len(items)
            skipped_items = 0
            
            # Process feed items
            for item in items:
                try:
                    # Skip non-ad items
                    if not isinstance(item, dict) or item.get('type') != 'ad':
                        skipped_items += 1
                        continue
                    
                    # Get the listing ID - try multiple possible locations
                    listing_id = None
                    id_fields = ['id', 'link_token', 'order_type_id', 'ad_number', 'record_id', 'uid']
                    
                    for field in id_fields:
                        if field in item and item[field]:
                            listing_id = str(item[field])
                            break
                    
                    # Skip if no valid ID found or if ID is '0'
                    if not listing_id or listing_id == '0':
                        skipped_items += 1
                        logger.warning(f"Skipping listing without valid ID. Available fields: {', '.join(item.keys())}")
                        logger.debug(f"Raw item data for skipped listing: {json.dumps(item, indent=2, ensure_ascii=False)}")
                        continue
                    
                    # Get the address details
                    street_name = item.get('street', '').strip()
                    street_number = str(item.get('address_home_number', '')).strip()
                    
                    # Create a complete listing object for exclusion check
                    listing_to_check = {
                        'address': {
                            'street': street_name,
                            'number': street_number,
                            'neighborhood': {'text': item.get('neighborhood', '')}
                        },
                        'title': item.get('title_1', '') or item.get('title', ''),
                        'description': item.get('info_text', ''),
                        'info_text': item.get('info_text', ''),
                        'row_1': item.get('row_1', '')
                    }
                    
                    # Check if the listing should be excluded
                    if is_excluded(listing_to_check):
                        logger.debug(f"Skipping excluded listing: {street_name} {street_number}")
                        continue
                    
                    # Parse details
                    rooms = None
                    square_meters = None
                    floor = None
                    price = None
                    
                    # Parse row_3 for rooms and square meters
                    row_3 = item.get('row_3', [])
                    if isinstance(row_3, list):
                        for detail in row_3:
                            detail_str = str(detail)
                            if 'חדרים' in detail_str:
                                try:
                                    rooms = float(detail_str.split()[0])
                                except (ValueError, IndexError):
                                    pass
                            elif 'מ"ר' in detail_str:
                                try:
                                    square_meters = int(detail_str.split()[0])
                                except (ValueError, IndexError):
                                    pass
                    
                    # Parse row_4 for price and floor
                    row_4 = item.get('row_4', [])
                    if isinstance(row_4, list):
                        for detail in row_4:
                            if isinstance(detail, dict):
                                if detail.get('key') == 'rooms':
                                    try:
                                        rooms = float(detail.get('value', 0))
                                    except (ValueError, TypeError):
                                        pass
                                elif detail.get('key') == 'floor':
                                    try:
                                        floor = int(detail.get('value', 0))
                                    except (ValueError, TypeError):
                                        pass
                                elif detail.get('key') == 'SquareMeter':
                                    try:
                                        if not square_meters:
                                            value = str(detail.get('value', '')).strip()
                                            if value:
                                                square_meters = int(value)
                                    except (ValueError, TypeError):
                                        pass
                    
                    # Try to parse price from the price field
                    if 'price' in item:
                        try:
                            # Remove currency symbol and commas, then convert to int
                            price_str = str(item['price']).replace('₪', '').replace(',', '').strip()
                            price = int(price_str)
                        except (ValueError, TypeError, AttributeError):
                            pass
                    
                    # Get coordinates
                    coords = item.get('coordinates', {})
                    latitude = coords.get('latitude')
                    longitude = coords.get('longitude')
                    
                    # Get dates
                    date_added = item.get('date_added')
                    updated_at = item.get('updated_at')
                    
                    # Build the listing object
                    parsed = {
                        'id': listing_id,
                        'type': listing_type,
                        'title': item.get('title_1', '') or item.get('title', ''),
                        'description': item.get('info_text', ''),  # Add info_text field
                        'price': price,
                        'address': {
                            'street': street_name,
                            'number': street_number,
                            'floor': floor,
                            'neighborhood': {'text': item.get('neighborhood', '')},
                            'city': {'text': item.get('city', 'תל אביב יפו')},
                            'coords': {
                                'latitude': latitude,
                                'longitude': longitude
                            }
                        },
                        'details': {
                            'rooms': rooms,
                            'square_meters': square_meters,
                            'square_meters_build': None,  # Not available in feed items
                            'condition': None,  # Not available in feed items
                            'date_added': date_added,
                            'updated_at': updated_at
                        },
                        'images': item.get('images_urls', []) or item.get('images', []),  # Try both fields
                        'cover_image': None,  # Will be set if images are available
                        'link': f"https://www.yad2.co.il/item/{listing_id}"
                    }
                    
                    # Set cover image if available
                    if parsed['images']:
                        parsed['cover_image'] = parsed['images'][0]
                    
                    # Clean up None values except for required fields
                    parsed = {k: v for k, v in parsed.items() if k == 'id' or v is not None}
                    listings.append(parsed)
                    
                except Exception as e:
                    logger.error(f"Error parsing listing: {str(e)}")
                    logger.debug(f"Raw item data for failed listing: {json.dumps(item, indent=2, ensure_ascii=False)}")
                    continue
            
            # Log summary of processed items
            if skipped_items > 0:
                logger.warning(f"Skipped {skipped_items} out of {total_items} items due to missing IDs")
            logger.info(f"Successfully processed {len(listings)} out of {total_items} items")
            
            return listings
            
        except Exception as e:
            logger.error(f"Error parsing listings: {str(e)}", exc_info=True)
            return []

    def parse_listing(self, item):
        """Parse a listing from the feed."""
        try:
            # Get basic listing info
            listing_id = item.get('id')
            if not listing_id:
                logger.warning(f"Skipping listing without valid ID. Available fields: {', '.join(item.keys())}")
                return None
            
            # Get the address details
            address_data = item.get('row_1', '')
            if isinstance(address_data, list):
                address_data = ' '.join(str(part) for part in address_data if part)
            
            # Parse address into components
            street_name = address_data.strip()  # In new format, row_1 is just the street name
            street_number = str(item.get('address_home_number', '')).strip()
            
            # Create listing object
            listing = {
                'id': listing_id,
                'title': item.get('title', ''),
                'type': item.get('type', ''),
                'price': item.get('price', 0),
                'address': {
                    'street': street_name,
                    'number': street_number,
                    'floor': item.get('floor', ''),
                    'city': item.get('city', ''),
                    'neighborhood': item.get('neighborhood', '')
                },
                'details': {
                    'rooms': item.get('rooms', ''),
                    'square_meters': item.get('square_meters', ''),
                    'square_meters_build': item.get('square_meters_build', ''),
                    'date_added': item.get('date_added', ''),
                    'date_updated': item.get('date_updated', '')
                },
                'images': item.get('images', []),
                'cover_image': item.get('cover_image', ''),
                'link': f"https://www.yad2.co.il/item/{listing_id}"
            }
            
            # Add agency info if present
            if 'agency' in item:
                listing['agency'] = item['agency']
            
            # Add tags if present
            if 'tags' in item:
                listing['tags'] = item['tags']
            
            return listing
            
        except Exception as e:
            logger.error(f"Error parsing listing: {str(e)}")
            return None 