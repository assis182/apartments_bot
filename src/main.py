import os
from dotenv import load_dotenv
from src.scraper import Yad2Scraper
from src.notifier import TelegramNotifier
import json
from datetime import datetime, timedelta
import logging
import pathlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

def print_listing(listing):
    """Print a single listing in a readable format."""
    print("\n" + "="*80)
    print(f"Title: {listing['title']}")
    print(f"Type: {listing['type']}")
    print(f"Price: ₪{listing['price']:,}")
    
    # Print address
    address = listing['address']
    print(f"Address: {address['street']} {address['number']}, Floor {address['floor']}")
    print(f"Location: {address['neighborhood']}, {address['city']}")
    
    # Print details
    details = listing['details']
    print(f"Rooms: {details['rooms']}")
    print(f"Size: {details['square_meters']}m² (Built: {details['square_meters_build']}m²)")
    
    # Print agency if it's an agency listing
    if 'agency' in listing:
        print(f"Agency: {listing['agency']}")
    
    # Print tags if present
    if 'tags' in listing:
        print(f"Tags: {', '.join(listing['tags'])}")
    
    # Print link
    print(f"Link: {listing['link']}")
    
    # Print images
    print(f"Images: {len(listing['images'])} images available")
    print(f"Cover image: {listing['cover_image']}")

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
            return datetime.fromisoformat(f.read().strip())
    except FileNotFoundError:
        return None

def save_last_digest_time(dt):
    """Save the timestamp of the last daily digest."""
    with open(get_file_path('last_digest.txt'), 'w') as f:
        f.write(dt.isoformat())

def is_listing_changed(old_listing, new_listing):
    """Check if a listing has been updated."""
    relevant_fields = ['price', 'title', 'details', 'address']
    old = old_listing.get('details', {})
    new = new_listing.get('details', {})
    
    for field in relevant_fields:
        if old.get(field) != new.get(field):
            return True
    return False

def should_send_daily_digest():
    """Check if it's time to send the daily digest."""
    if not os.getenv('CONTAINER_ENV'):
        return False  # Never send daily digest in local mode
        
    last_digest = load_last_digest_time()
    if not last_digest:
        return True
        
    now = datetime.now()
    # If it's a new day and it's after 9 AM Israel time (UTC+3)
    israel_hour = (now.hour + 3) % 24  # Convert to Israel time
    return (now.date() > last_digest.date() and israel_hour >= 9)

def format_daily_digest(tracked_listings):
    """Format the daily digest message."""
    listings = [info['details'] for info in tracked_listings.values()]
    listings.sort(key=lambda x: x.get('price', 0))  # Sort by price
    
    message = ["📋 <b>Daily Apartments Digest</b>\n"]
    message.append(f"Total active listings: {len(listings)}\n")
    
    for listing in listings:
        message.append(notifier.format_listing_message(listing))
        message.append("-" * 30)
    
    return "\n".join(message)

def main():
    """Main entry point for the scraper."""
    # Load environment variables
    load_dotenv()
    
    # Create scraper instance
    scraper = Yad2Scraper()
    
    # Create notifier instance
    notifier = TelegramNotifier()
    
    # Load tracked listings
    tracked_listings = load_tracked_listings()
    
    logger.info("Searching for listings...")
    current_listings = scraper.search_listings()
    
    # Convert current listings to a dictionary for easier comparison
    current_listings_dict = {str(listing['id']): listing for listing in current_listings}
    
    # Find new, updated, and removed listings
    new_listings = []
    updated_listings = []
    removed_listings = []
    
    # Check for new and updated listings
    for listing_id, listing in current_listings_dict.items():
        if listing_id not in tracked_listings:
            new_listings.append(listing)
            tracked_listings[listing_id] = {
                'first_seen': datetime.now().isoformat(),
                'details': listing
            }
        elif is_listing_changed(tracked_listings[listing_id]['details'], listing):
            updated_listings.append(listing)
            tracked_listings[listing_id]['details'] = listing
    
    # Check for removed listings
    for listing_id, tracked_info in list(tracked_listings.items()):
        if listing_id not in current_listings_dict:
            removed_listings.append(tracked_info['details'])
            del tracked_listings[listing_id]
    
    # Save updated tracked listings
    save_tracked_listings(tracked_listings)
    
    # Print summary
    logger.info(f"Found {len(current_listings)} total listings")
    logger.info(f"Found {len(new_listings)} new listings")
    logger.info(f"Found {len(updated_listings)} updated listings")
    logger.info(f"Found {len(removed_listings)} removed listings")
    
    # Check if we should send a daily digest
    if should_send_daily_digest():
        logger.info("Sending daily digest...")
        digest_message = format_daily_digest(tracked_listings)
        notifier.notify_new_listings_sync([{"custom_message": digest_message}])
        save_last_digest_time(datetime.now())
    
    # Send notifications for changes
    if new_listings or updated_listings or removed_listings:
        notifications = []
        
        # Format new listings
        if new_listings:
            notifications.append("🆕 <b>New Listings:</b>")
            for listing in new_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Format updated listings
        if updated_listings:
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("📝 <b>Updated Listings:</b>")
            for listing in updated_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Format removed listings
        if removed_listings:
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("❌ <b>Removed Listings:</b>")
            for listing in removed_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Send all notifications as one message
        notifier.notify_new_listings_sync([{"custom_message": "\n\n".join(notifications)}])
    else:
        logger.info("No changes in listings")
    
    # Save current results to a file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"listings_{timestamp}.json"
    
    with open(get_file_path(filename), 'w', encoding='utf-8') as f:
        json.dump(current_listings, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Results saved to {filename}")

if __name__ == "__main__":
    main() 