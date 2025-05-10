import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # API Configuration
    API_URL = os.getenv('YAD2_API_URL', 'https://www.yad2.co.il')
    USER_AGENT = os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36')

    # Search Parameters
    MIN_ROOMS = int(os.getenv('MIN_ROOMS', 3))
    MAX_ROOMS = int(os.getenv('MAX_ROOMS', 4))
    PARKING = int(os.getenv('PARKING', 1))
    SHELTER = int(os.getenv('SHELTER', 1))
    NEIGHBORHOODS = os.getenv('NEIGHBORHOODS', '1483,204,1516').split(',')
    PROPERTY_CONDITION = os.getenv('PROPERTY_CONDITION', '1,6,2').split(',')

    # Headers
    @classmethod
    def get_headers(cls):
        return {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9,he;q=0.8",
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "origin": cls.API_URL,
            "user-agent": cls.USER_AGENT,
            "dnt": "1",
            "uzlc": "true",
        }

    EXCLUDED_STREETS = [
        "ויסוצקי",
        # Add more street names as needed
    ] 