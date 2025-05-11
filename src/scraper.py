import requests
from src.config import Config
import json
import time
import random
import re
import os
from datetime import datetime
import logging
from src.utils import get_data_dir, logger
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
                
                # Add timeout
                kwargs['timeout'] = self.config.REQUEST_TIMEOUT
                
                # Make the request
                response = self.session.request(method, url, **kwargs)
                
                # Check for anti-bot detection
                if self._is_bot_detected(response):
                    logger.warning(f"Anti-bot detection triggered (attempt {attempt + 1}/{max_retries})")
                    self.failed_attempts += 1
                    self._handle_bot_detection()
                    continue
                
                # Reset failed attempts on success
                self.failed_attempts = 0
                return response
                
            except (RequestException, ProxyError) as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    self._handle_request_failure()
                    continue
                raise

    def _is_bot_detected(self, response):
        """Check if the response indicates bot detection."""
        if response.status_code != 200:
            return True
            
        # Check response content for bot detection indicators
        content_lower = response.text.lower()
        bot_indicators = [
            'captcha',
            'shield',
            'automated',
            'bot',
            'security check',
            'verify you are human'
        ]
        
        return any(indicator in content_lower for indicator in bot_indicators)

    def _handle_bot_detection(self):
        """Handle bot detection by adjusting behavior."""
        # Increase delays based on number of failed attempts
        base_delay = self.config.RETRY_DELAY
        if self.config.PROGRESSIVE_DELAYS:
            base_delay *= (1 + self.failed_attempts)
        
        # Add some randomness to the delay
        delay = base_delay + random.uniform(1, 3)
        logger.info(f"Waiting {delay:.1f} seconds before retry...")
        time.sleep(delay)
        
        # Rotate browser profile
        self._setup_session()

    def _handle_request_failure(self):
        """Handle request failure by rotating proxy and waiting."""
        if self.config.USE_PROXY:
            self._get_next_proxy()
        time.sleep(self.config.RETRY_DELAY)

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
        # Generate consistent device fingerprint
        device_id = self._generate_device_id()
        
        # More sophisticated browser fingerprinting
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
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'X-Device-Id': device_id,
            'X-Platform': 'desktop',
            'X-App-Version': '1.0.0',
        })
        logger.debug("Session headers configured")

    def _generate_device_id(self):
        """Generate a consistent device ID based on container/environment."""
        # Use environment variables or system info to generate a consistent ID
        system_info = f"{os.uname().nodename}-{os.uname().machine}"
        device_id = hashlib.md5(system_info.encode()).hexdigest()
        return device_id

    def _simulate_browser_behavior(self):
        """Simulate realistic browser behavior."""
        logger.debug("Simulating browser behavior")
        
        try:
            # Get browser profile
            profile = self._get_browser_profile()
            
            # Update headers with profile information
            self.session.headers.update({
                'User-Agent': profile['user_agent'],
                'Sec-Ch-Ua-Platform': f'"{profile["platform"]}"',
                'Sec-Ch-Width': str(profile['viewport']['width']),
                'Sec-Ch-Viewport-Width': str(profile['viewport']['width']),
                'Viewport-Width': str(profile['viewport']['width']),
            })

            # Visit Google search first
            search_query = "yad2 תל אביב דירות להשכרה"
            encoded_query = urlencode({'q': search_query})
            self._make_request('GET', 
                f'https://www.google.com/search?{encoded_query}',
                headers={'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
            )
            time.sleep(random.uniform(2, 4))

            # Visit Yad2 homepage through Google search
            home_response = self._make_request('GET',
                'https://www.yad2.co.il',
                headers={
                    'Referer': f'https://www.google.com/search?{encoded_query}',
                    'Sec-Fetch-Site': 'cross-site',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-User': '?1',
                }
            )
            self._save_cookies()
            time.sleep(random.uniform(3, 5))

            # Visit real estate section
            realestate_response = self._make_request('GET',
                'https://www.yad2.co.il/realestate/rent',
                headers={
                    'Referer': 'https://www.yad2.co.il',
                    'Sec-Fetch-Site': 'same-origin',
                }
            )
            self._save_cookies()

            # Extract CSRF token
            csrf_token = None
            for response in [home_response, realestate_response]:
                match = re.search(r'csrf-token"\s+content="([^"]+)"', response.text)
                if match:
                    csrf_token = match.group(1)
                    self.session.headers.update({
                        'X-CSRF-TOKEN': csrf_token,
                        'X-Requested-With': 'XMLHttpRequest'
                    })
                    break

            # Simulate progressive search refinement
            self._simulate_search_refinement()

        except Exception as e:
            logger.error(f"Error during browser simulation: {str(e)}", exc_info=True)

    def _simulate_search_refinement(self):
        """Simulate a user progressively refining their search."""
        base_url = 'https://www.yad2.co.il/realestate/rent'
        
        # Start with basic search
        params = []
        search_sequence = [
            ('city', '5000'),  # Tel Aviv
            ('property', '1'),  # Apartments
            ('rooms', '3-4'),  # Room range
            ('price', '0-13000'),  # Price range
        ]

        for param in search_sequence:
            params.append(param)
            url = f"{base_url}?{urlencode(params)}"
            
            self._make_request('GET', url, 
                headers={
                    'Referer': base_url,
                    'Sec-Fetch-Site': 'same-origin',
                }
            )
            time.sleep(random.uniform(2, 4))

        self._save_cookies()

    def search_listings(self):
        """Search for listings using the JSON API."""
        try:
            # Log environment info
            is_container = os.getenv('CONTAINER_ENV') == 'true'
            logger.info(f"Running in container: {is_container}")
            logger.info(f"Python version: {sys.version}")
            logger.info(f"Current time: {datetime.now().isoformat()}")
            logger.info(f"Current timezone: {time.tzname}")
            
            # Initialize browser environment
            self._simulate_browser_behavior()
            
            all_listings = []
            any_request_succeeded = False
            
            for neighborhood_name in self.config.NEIGHBORHOODS:
                logger.info(f"Searching in {neighborhood_name}...")
                
                try:
                    # Prepare search parameters
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
                    
                    # Make the API request with our enhanced request handler
                    response = self._make_request(
                        'GET',
                        f"{self.config.API_URL}/api/feed/get",
                        params=search_params,
                        headers={
                            'Accept': 'application/json, text/plain, */*',
                            'Referer': 'https://www.yad2.co.il/realestate/rent',
                            'Sec-Fetch-Site': 'same-origin',
                            'Sec-Fetch-Mode': 'cors',
                            'Sec-Fetch-Dest': 'empty'
                        }
                    )
                    
                    # Process the response
                    if response and response.status_code == 200:
                        try:
                            data = response.json()
                            
                            if 'feed' in data and 'feed_items' in data['feed']:
                                any_request_succeeded = True
                                neighborhood_listings = self.parse_listings(data['feed'])
                                
                                filtered_listings = [
                                    listing for listing in neighborhood_listings
                                    if listing.get('address', {}).get('neighborhood') == neighborhood_name
                                ]
                                
                                logger.info(f"Found {len(filtered_listings)} listings in {neighborhood_name}")
                                all_listings.extend(filtered_listings)
                                
                                # Add a natural delay between neighborhoods
                                if neighborhood_name != self.config.NEIGHBORHOODS[-1]:
                                    time.sleep(random.uniform(
                                        self.config.MIN_REQUEST_DELAY,
                                        self.config.MAX_REQUEST_DELAY
                                    ))
                            else:
                                logger.warning(f"No feed data found for {neighborhood_name}")
                                
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse JSON response for {neighborhood_name}: {str(e)}")
                            logger.debug(f"Response preview: {response.text[:500]}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error processing neighborhood {neighborhood_name}: {str(e)}", exc_info=True)
                    continue
            
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