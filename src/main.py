import os
from dotenv import load_dotenv
from src.scraper import Yad2Scraper
from src.notifier import TelegramNotifier
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        with open('/app/data/tracked_listings.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_tracked_listings(tracked_listings):
    """Save tracked listings with their details to file."""
    with open('/app/data/tracked_listings.json', 'w', encoding='utf-8') as f:
        json.dump(tracked_listings, f, ensure_ascii=False, indent=2)

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
    
    # Find new and removed listings
    new_listings = []
    removed_listings = []
    
    # Check for new listings
    for listing_id, listing in current_listings_dict.items():
        if listing_id not in tracked_listings:
            new_listings.append(listing)
            # Add to tracked listings with timestamp
            tracked_listings[listing_id] = {
                'first_seen': datetime.now().isoformat(),
                'details': listing
            }
    
    # Check for removed listings
    for listing_id, tracked_info in list(tracked_listings.items()):
        if listing_id not in current_listings_dict:
            removed_listings.append(tracked_info['details'])
            # Remove from tracked listings
            del tracked_listings[listing_id]
    
    # Save updated tracked listings
    save_tracked_listings(tracked_listings)
    
    # Print summary
    logger.info(f"Found {len(current_listings)} total listings")
    logger.info(f"Found {len(new_listings)} new listings")
    logger.info(f"Found {len(removed_listings)} removed listings")
    
    # Send notifications for changes
    if new_listings or removed_listings:
        notifications = []
        
        # Format new listings
        if new_listings:
            notifications.append("🆕 New Listings:")
            for listing in new_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Format removed listings
        if removed_listings:
            if new_listings:  # Add separator if we had new listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("❌ Removed Listings:")
            for listing in removed_listings:
                # Add a "REMOVED" prefix to the listing message
                msg = notifier.format_listing_message(listing)
                notifications.append(msg)
        
        # Send all notifications as one message
        notifier.notify_new_listings_sync([{"custom_message": "\n\n".join(notifications)}])
    else:
        logger.info("No changes in listings")
    
    # Save current results to a file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"/app/data/listings_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(current_listings, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Results saved to {filename}")

if __name__ == "__main__":
    main() 