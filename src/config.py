import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # API Configuration
    YAD2_API_URL = os.getenv('YAD2_API_URL', 'https://www.yad2.co.il')
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36')

    # Search Parameters
    TOP_AREA = int(os.getenv('TOP_AREA', 2))  # Tel Aviv area
    AREA = int(os.getenv('AREA', 1))  # Tel Aviv city
    CITY = int(os.getenv('CITY', 5000))  # Tel Aviv
    PROPERTY_TYPE = int(os.getenv('PROPERTY_TYPE', 1))  # Apartment
    MIN_ROOMS = int(os.getenv('MIN_ROOMS', 3))
    MAX_ROOMS = int(os.getenv('MAX_ROOMS', 4))
    ROOMS_RANGE = f"{MIN_ROOMS}-{MAX_ROOMS}"
    PRICE_RANGE = os.getenv('PRICE_RANGE', '-1-13000')  # Up to 13,000 NIS
    PARKING = int(os.getenv('PARKING', 1))
    SHELTER = int(os.getenv('SHELTER', 1))
    NEIGHBORHOODS = os.getenv('NEIGHBORHOODS', '1483,204,1516').split(',')  # IDs for: הצפון החדש - כיכר המדינה, הצפון החדש - צפון, הצפון הישן - צפון
    PROPERTY_CONDITION = os.getenv('PROPERTY_CONDITION', '1,6,2').split(',')

    # Proxy configuration
    USE_PROXY = False  # Set to False to disable proxy
    PROXY_ROTATION_ENABLED = False
    PROXY_URLS = []
    
    # Request configuration
    MAX_RETRIES = 5  # Increased retries
    RETRY_DELAY = 3  # seconds
    REQUEST_TIMEOUT = 20  # seconds
    
    # Browser profiles - rotate between these
    BROWSER_PROFILES = [
        {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'platform': 'macOS',
            'viewport': {'width': 1440, 'height': 900},
            'language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        {
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'platform': 'Windows',
            'viewport': {'width': 1920, 'height': 1080},
            'language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7'
        },
        {
            'user_agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'platform': 'Linux',
            'viewport': {'width': 1680, 'height': 1050},
            'language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7'
        }
    ]
    
    # Anti-bot evasion settings
    MIN_REQUEST_DELAY = 2
    MAX_REQUEST_DELAY = 5
    PROGRESSIVE_DELAYS = True  # Increase delays after failed attempts

    # Headers
    @classmethod
    def get_headers(cls):
        return {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,he;q=0.8",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "origin": cls.YAD2_API_URL,
            "user-agent": cls.USER_AGENT,
            "dnt": "1",
            "uzlc": "true",
        } 