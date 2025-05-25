import os
import pathlib
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json

def get_data_dir():
    """Get the appropriate data directory based on environment."""
    # Check if we're running in a container
    if os.getenv('CONTAINER_ENV') == 'true':
        base_dir = '/app/data'
    else:
        # Use a local directory in the project root
        base_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    
    # Create the directory if it doesn't exist
    pathlib.Path(base_dir).mkdir(parents=True, exist_ok=True)
    return base_dir

def get_file_path(filename):
    """Get the full path for a file in the data directory."""
    return os.path.join(get_data_dir(), filename)

def setup_logging():
    """Configure logging to both file and stdout."""
    try:
        # First set up a basic console logger in case something fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        basic_logger = logging.getLogger(__name__)
        
        # Get data directory
        data_dir = get_data_dir()
        basic_logger.info(f"Data directory: {data_dir}")
        
        # Create logs directory
        log_dir = os.path.join(data_dir, 'logs')
        pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
        basic_logger.info(f"Log directory: {log_dir}")
        
        # Create a rotating file handler
        log_file = os.path.join(log_dir, 'yad2_scraper.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        basic_logger.info(f"Created rotating file handler for: {log_file}")
        
        # Create console handler that writes to the cron.log
        cron_log = os.path.join(data_dir, 'cron.log')
        cron_handler = logging.FileHandler(cron_log)
        cron_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        basic_logger.info(f"Created cron log handler for: {cron_log}")
        
        # Create stdout handler for container logs
        stdout_handler = logging.StreamHandler()
        stdout_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        basic_logger.info("Created stdout handler for container logs")
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add our handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(cron_handler)
        root_logger.addHandler(stdout_handler)  # Add stdout handler
        
        # Log environment configuration
        logger = logging.getLogger(__name__)
        logger.info("Environment configuration:")
        logger.info(f"  TELEGRAM_BOT_TOKEN: {'✓ Set' if os.getenv('TELEGRAM_BOT_TOKEN') else '✗ Not set'}")
        logger.info(f"  TELEGRAM_CHAT_ID: {'✓ Set' if os.getenv('TELEGRAM_CHAT_ID') else '✗ Not set'}")
        logger.info(f"  CONTAINER_ENV: {'✓ Set' if os.getenv('CONTAINER_ENV') else '✗ Not set'}")
        logger.info(f"  YAD2_API_URL: {os.getenv('YAD2_API_URL', 'https://www.yad2.co.il')}")
        
        logger.info("Logging setup completed successfully")
        return logger
        
    except Exception as e:
        # If something goes wrong, set up basic console logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Error setting up logging: {str(e)}", exc_info=True)
        logger.info("Falling back to basic console logging")
        return logger

def load_tracked_listings():
    """Load tracked listings from file with their details."""
    try:
        with open(get_file_path('tracked_listings.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_tracked_listings(tracked_listings):
    """Save tracked listings with their details to file."""
    with open(get_file_path('tracked_listings.json'), 'w', encoding='utf-8') as f:
        json.dump(tracked_listings, f, ensure_ascii=False, indent=2)

def load_last_digest_time():
    """Load the timestamp of the last daily digest."""
    try:
        with open(get_file_path('last_digest.txt'), 'r') as f:
            content = f.read().strip()
            if not content:
                return None
            return content
    except FileNotFoundError:
        return None

def save_last_digest_time(dt):
    """Save the timestamp of the last daily digest."""
    with open(get_file_path('last_digest.txt'), 'w') as f:
        f.write(dt.isoformat())

def verify_worker_run():
    """Create or update files to track worker runs."""
    timestamp = datetime.now().isoformat()
    
    # Save last run time
    run_file = os.path.join(get_data_dir(), 'last_worker_run.txt')
    try:
        with open(run_file, 'w') as f:
            f.write(timestamp)
    except Exception as e:
        logger.error(f"Failed to write worker run file: {str(e)}")
    
    # Append to run history (keep last 100 runs)
    history_file = os.path.join(get_data_dir(), 'worker_run_history.txt')
    try:
        # Read existing history
        lines = []
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                lines = f.readlines()
        
        # Add new run
        lines.append(f"{timestamp}\n")
        
        # Keep last 100 runs
        lines = lines[-100:]
        
        # Write back
        with open(history_file, 'w') as f:
            f.writelines(lines)
    except Exception as e:
        logger.error(f"Failed to update worker run history: {str(e)}")

def verify_cron_run():
    """Create or update a file to track cron runs."""
    cron_file = os.path.join(get_data_dir(), 'last_cron_run.txt')
    try:
        with open(cron_file, 'w') as f:
            f.write(datetime.now().isoformat())
        logger.info(f"Cron run verified and saved to {cron_file}")
    except Exception as e:
        logger.error(f"Failed to write cron verification file: {str(e)}")

def get_exclusions_file():
    """Get the path to the exclusions file."""
    return get_file_path('exclusions.json')

def load_exclusions():
    """Load the list of excluded apartment IDs and streets."""
    try:
        with open(get_exclusions_file(), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_exclusions(exclusions):
    """Save the list of excluded apartment IDs and streets."""
    with open(get_exclusions_file(), 'w', encoding='utf-8') as f:
        # If it's a dictionary, convert to list
        if isinstance(exclusions, dict):
            exclusions = list(exclusions.values())
        json.dump(exclusions, f, ensure_ascii=False, indent=2)

def add_to_exclusions(listing, reason="Manually excluded"):
    """Add a listing to the exclusions list."""
    exclusions = load_exclusions()
    listing_id = str(listing.get('id', ''))
    address = listing.get('address', {})
    street = address.get('street', '').strip()
    number = str(address.get('number', '')).strip()
    full_address = f"{street} {number}".strip()
    
    # Create exclusion entry
    exclusion_entry = {
        'id': listing_id,
        'title': listing.get('title', ''),
        'address': {
            'street': street,
            'number': number,
            'full': full_address
        },
        'excluded_at': datetime.now().isoformat(),
        'reason': reason
    }
    
    # Add to exclusions list
    exclusions.append(exclusion_entry)
    save_exclusions(exclusions)
    logger.info(f"Added listing {listing_id} ({full_address}) to exclusions list")
    return exclusions

def remove_from_exclusions(listing_id):
    """Remove a listing from the exclusions list."""
    exclusions = load_exclusions()
    listing_id = str(listing_id)
    
    if listing_id in exclusions:
        del exclusions[listing_id]
        save_exclusions(exclusions)
        logger.info(f"Removed listing {listing_id} from exclusions list")
    return exclusions

def add_listing_to_exclusions(listing_id, title="", reason="Manually excluded listing"):
    """Add a specific listing ID to the exclusions list."""
    exclusions = load_exclusions()
    
    # Create exclusion entry
    exclusion_entry = {
        'id': listing_id,
        'title': title or 'Manually excluded listing',
        'address': {},  # Empty address since we're excluding by ID
        'excluded_at': datetime.now().isoformat(),
        'reason': reason,
        'exclude_by_id': True  # Flag to indicate this is an ID-based exclusion
    }
    
    # Add to exclusions list
    exclusions.append(exclusion_entry)
    save_exclusions(exclusions)
    logger.info(f"Added listing ID {listing_id} to exclusions list")
    return exclusions

def is_excluded(listing):
    """Check if a listing is excluded based on ID, address, or street."""
    logger = logging.getLogger(__name__)
    exclusions = load_exclusions()
    
    # First check if the listing ID is directly excluded
    listing_id = str(listing.get('id', ''))
    for exclusion in exclusions:
        if exclusion.get('exclude_by_id') and exclusion['id'] == listing_id:
            logger.info(f"Listing excluded - exact ID match: '{listing_id}'")
            return True
    
    # Get and sanitize address components from the listing
    address = listing.get('address', {})
    if not isinstance(address, dict):
        logger.warning(f"Invalid address format in listing: {address}")
        return False
        
    # Get the full street name from the listing (including number if present)
    listing_street = (address.get('street', '') or '').strip()
    listing_number = (address.get('number', '') or '').strip()
    
    # Create full address string (both with and without space)
    full_address_with_space = f"{listing_street} {listing_number}".strip()
    full_address_no_space = f"{listing_street}{listing_number}".strip()
    
    # Get other text fields that might contain the street name
    listing_title = (listing.get('title', '') or '').strip()
    listing_description = (listing.get('description', '') or '').strip()
    listing_info_text = (listing.get('info_text', '') or '').strip()
    listing_row_1 = (listing.get('row_1', '') or '').strip()
    
    # Combine all text fields for searching
    searchable_text = [
        listing_street,
        full_address_with_space,
        full_address_no_space,
        listing_title,
        listing_description,
        listing_info_text,
        listing_row_1,
        address.get('full', ''),
        address.get('neighborhood', {}).get('text', ''),
        listing.get('neighborhood', '')  # New API format has neighborhood at root level
    ]
    searchable_text = ' '.join(text for text in searchable_text if text).lower()
    
    if not listing_street:
        logger.warning("Listing has no street name, but will still check other fields")
    
    logger.debug(f"Checking exclusions for listing - Street: '{listing_street}', Number: '{listing_number}', Full: '{full_address_with_space}'")
    logger.debug(f"Searchable text: {searchable_text}")
    
    # Check each exclusion
    for exclusion in exclusions:
        # Skip ID-based exclusions as we've already checked them
        if exclusion.get('exclude_by_id'):
            continue
            
        # Get and sanitize the excluded address
        excluded_address = exclusion.get('address', {})
        if not isinstance(excluded_address, dict):
            logger.warning(f"Invalid exclusion address format: {excluded_address}")
            continue
            
        excluded_street = (excluded_address.get('street', '') or '').strip()
        excluded_number = (excluded_address.get('number', '') or '').strip()
        excluded_full = (excluded_address.get('full', '') or '').strip()
        
        # If it's an entire street exclusion
        if exclusion.get('exclude_entire_street'):
            # Normalize both street names for comparison
            normalized_listing_street = listing_street.lower().strip()
            normalized_excluded_street = excluded_street.lower().strip()
            
            # Check if the street name appears in any of the text fields
            if normalized_excluded_street in normalized_listing_street:
                logger.info(f"Listing excluded - street '{excluded_street}' matches listing street '{listing_street}'")
                return True
                
            # Also check if the street name appears in any other text field
            if normalized_excluded_street in searchable_text:
                logger.info(f"Listing excluded - street '{excluded_street}' found in listing text")
                return True
                
            logger.debug(f"Street '{excluded_street}' not found in listing text")
        else:
            # For specific addresses, check both split and combined formats
            # First check if the full address matches (with or without space)
            if excluded_full and (excluded_full == full_address_with_space or excluded_full == full_address_no_space):
                logger.info(f"Listing excluded - exact full address match: '{excluded_full}'")
                return True
            
            # Then check if the street and number match separately
            if excluded_street == listing_street and (not excluded_number or excluded_number == listing_number):
                logger.info(f"Listing excluded - street and number match: '{listing_street} {listing_number}'")
                return True
            
            # Also check if the excluded street appears in the full address
            if excluded_street in full_address_with_space or excluded_street in full_address_no_space:
                logger.info(f"Listing excluded - street found in full address: '{excluded_street}' in '{full_address_with_space}'")
                return True
            
            logger.debug(f"Address '{full_address_with_space}' does not match excluded address '{excluded_full}'")
    
    logger.debug(f"Listing not excluded: '{full_address_with_space}'")
    return False

def add_address_to_exclusions(street, number, reason="Manually excluded"):
    """Add a specific address to the exclusions list."""
    exclusions = load_exclusions()
    full_address = f"{street} {number}".strip()
    
    # Create exclusion entry
    exclusion_entry = {
        'id': '',  # No ID for manual address exclusions
        'title': 'Manually excluded address',
        'address': {
            'street': full_address,  # Store the full address in the street field
            'number': '',  # Not needed anymore since full address is in street
            'full': full_address
        },
        'excluded_at': datetime.now().isoformat(),
        'reason': reason
    }
    
    # Add to exclusions list
    exclusions.append(exclusion_entry)
    save_exclusions(exclusions)
    logger.info(f"Added address {full_address} to exclusions list")
    return exclusions

def add_street_to_exclusions(street, reason="Manually excluded street"):
    """Add an entire street to the exclusions list."""
    exclusions = load_exclusions()
    
    # Create exclusion entry for the entire street
    exclusion_entry = {
        'id': '',
        'title': 'Manually excluded street',
        'address': {
            'street': street,
            'number': '*',  # Wildcard to indicate entire street
            'full': f"{street} *"
        },
        'excluded_at': datetime.now().isoformat(),
        'reason': reason,
        'exclude_entire_street': True
    }
    
    # Add to exclusions list
    exclusions.append(exclusion_entry)
    save_exclusions(exclusions)
    logger.info(f"Added entire street {street} to exclusions list")
    return exclusions

def is_street_excluded(street):
    """Check if an entire street is excluded."""
    exclusions = load_exclusions()
    
    # Clean up the input street name - remove any numbers and extra spaces
    street = ' '.join(word for word in street.split() if not any(c.isdigit() for c in word)).strip()
    
    # Check for street-level exclusions
    items = exclusions.values() if isinstance(exclusions, dict) else exclusions
    for item in items:
        if item.get('exclude_entire_street'):
            excluded_street = item['address']['street'].strip()
            if street == excluded_street:
                return True
    return False

# Initialize logger
logger = setup_logging() 