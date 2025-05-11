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
        """Setup the session with mobile app headers."""
        # Generate a consistent device ID
        device_id = self._generate_device_id()
        
        # Simulate Yad2's mobile app
        self.session.headers.update({
            'User-Agent': 'Yad2 Android App v5.0.0',
            'X-Yad2-App-Version': '5.0.0',
            'X-Yad2-Device-Id': device_id,
            'X-Yad2-Device-Type': 'android',
            'Accept': 'application/json',
            'Accept-Language': 'he-IL',
            'Accept-Encoding': 'gzip',
            'Connection': 'Keep-Alive',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'www.yad2.co.il',
            'Cache-Control': 'no-cache'
        })
        logger.debug("Session headers configured for mobile app")

    def _generate_device_id(self):
        """Generate a consistent device ID based on container/environment."""
        # Use environment variables or system info to generate a consistent ID
        system_info = f"{os.uname().nodename}-{os.uname().machine}"
        device_id = hashlib.md5(system_info.encode()).hexdigest()
        return device_id

    def _simulate_browser_behavior(self):
        """Simulate mobile app initialization."""
        logger.debug("Simulating mobile app behavior")
        
        try:
            # Initial app launch request
            launch_response = self._make_request('GET',
                'https://www.yad2.co.il/api/v2/app/init',
                headers={
                    'Accept': 'application/json',
                }
            )
            time.sleep(random.uniform(1, 2))

            # Get feed token
            token_response = self._make_request('GET',
                'https://www.yad2.co.il/api/v2/feed/token',
                headers={
                    'Accept': 'application/json',
                }
            )
            
            if token_response and token_response.status_code == 200:
                try:
                    token_data = token_response.json()
                    if 'token' in token_data:
                        self.session.headers.update({
                            'X-Yad2-Feed-Token': token_data['token']
                        })
                except json.JSONDecodeError:
                    pass

            time.sleep(random.uniform(1, 2))

        except Exception as e:
            logger.error(f"Error during mobile app simulation: {str(e)}", exc_info=True)

    def search_listings(self):
        """Search for listings using the mobile API."""
        try:
            # Log environment info
            is_container = os.getenv('CONTAINER_ENV') == 'true'
            logger.info(f"Running in container: {is_container}")
            logger.info(f"Python version: {sys.version}")
            logger.info(f"Current time: {datetime.now().isoformat()}")
            logger.info(f"Current timezone: {time.tzname}")
            
            # Initialize mobile app environment
            self._simulate_browser_behavior()
            
            all_listings = []
            any_request_succeeded = False
            
            for neighborhood_name in self.config.NEIGHBORHOODS:
                logger.info(f"Searching in {neighborhood_name}...")
                
                try:
                    # Mobile API search parameters
                    search_params = {
                        "cat": 2,
                        "subcat": 2,
                        "city": 5000,
                        "neighborhood": neighborhood_name,
                        "rooms": f"{self.config.MIN_ROOMS}-{self.config.MAX_ROOMS}",
                        "price": "-1-13000",
                        "parking": "1",
                        "shelter": "1",
                        "page": 1,
                        "limit": 50,
                        "filters": "parking=1&shelter=1"
                    }
                    
                    # Make the API request
                    response = self._make_request(
                        'GET',
                        "https://www.yad2.co.il/api/v2/feed/feed",
                        params=search_params,
                        headers={
                            'Accept': 'application/json',
                        }
                    )
                    
                    if response and response.status_code == 200:
                        try:
                            data = response.json()
                            
                            # Mobile API has a different response structure
                            if 'data' in data and 'feed' in data['data']:
                                any_request_succeeded = True
                                neighborhood_listings = self.parse_listings(data['data'])
                                
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
        """Parse the listings from the mobile API response."""
        try:
            listings = []
            
            # Handle mobile API response structure
            feed_items = data.get('feed', [])
            
            for item in feed_items:
                try:
                    parsed = {
                        'id': item.get('id'),
                        'type': 'mobile',
                        'title': f"{item.get('type_title', '')} - {item.get('street', '')} {item.get('house_number', '')}",
                        'price': item.get('price'),
                        'address': {
                            'street': item.get('street'),
                            'number': item.get('house_number'),
                            'floor': item.get('floor'),
                            'neighborhood': item.get('neighborhood'),
                            'city': item.get('city')
                        },
                        'details': {
                            'rooms': item.get('rooms'),
                            'square_meters': item.get('square_meters'),
                            'condition': item.get('property_condition')
                        },
                        'images': item.get('images', []),
                        'link': f"https://www.yad2.co.il/item/{item.get('id')}"
                    }
                    # Clean up None values
                    parsed = {k: v for k, v in parsed.items() if v is not None}
                    listings.append(parsed)
                except Exception as e:
                    logger.error(f"Error parsing listing: {str(e)}")
                    continue
            
            return listings
            
        except Exception as e:
            logger.error(f"Error parsing listings: {str(e)}", exc_info=True)
            return [] 