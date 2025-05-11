import os
from dotenv import load_dotenv
from src.scraper import Yad2Scraper
from src.notifier import TelegramNotifier
import json
from datetime import datetime, timedelta
import logging
import pathlib
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Configure logging to both file and stdout."""
    # Create logs directory
    log_dir = os.path.join(get_data_dir(), 'logs')
    pathlib.Path(log_dir).mkdir(parents=True, exist_ok=True)
    
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
    
    # Create console handler that writes to the cron.log
    cron_log = os.path.join(get_data_dir(), 'cron.log')
    cron_handler = logging.FileHandler(cron_log)
    cron_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(cron_handler)
    
    return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

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
    # First check price separately to track price changes
    old_price = old_listing.get('price')
    new_price = new_listing.get('price')
    if old_price != new_price:
        return True, 'price'
    
    # Then check other relevant fields
    relevant_fields = ['title', 'details', 'address']
    old = old_listing.get('details', {})
    new = new_listing.get('details', {})
    
    for field in relevant_fields:
        if old.get(field) != new.get(field):
            return True, field
            
    return False, None

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
    # Convert tracked listings to a list with first_seen date
    listings_with_dates = [
        {
            'first_seen': info['first_seen'],
            'details': info['details']
        } for info in tracked_listings.values()
    ]
    
    # Sort by first_seen date (most recent first)
    listings_with_dates.sort(key=lambda x: x['first_seen'], reverse=True)
    
    message = ["📋 <b>Daily Apartments Digest</b>\n"]
    message.append(f"Total active listings: {len(listings_with_dates)}\n")
    
    for listing_info in listings_with_dates:
        listing = listing_info['details']
        first_seen_date = datetime.fromisoformat(listing_info['first_seen']).strftime("%Y-%m-%d %H:%M")
        
        # Format the basic listing message
        listing_msg = notifier.format_listing_message(listing)
        
        # Add first seen date
        listing_msg += f"\n🕒 First seen: {first_seen_date}"
        
        message.append(listing_msg)
        message.append("-" * 30)
    
    return "\n".join(message)

def format_change_message(listing_id, old_listing, new_listing, change_type):
    """Format a message for a listing change."""
    if change_type == 'price':
        old_price = old_listing.get('price', 0)
        new_price = new_listing.get('price', 0)
        price_diff = new_price - old_price
        change_symbol = "📈" if price_diff > 0 else "📉"
        
        message = [f"{change_symbol} <b>Price Change Alert!</b>"]
        message.append(notifier.format_listing_message(new_listing))
        message.append(f"\nPrice changed from ₪{old_price:,} to ₪{new_price:,}")
        message.append(f"Difference: {'+' if price_diff > 0 else ''}{price_diff:,} ₪")
        
        return "\n".join(message)
    
    return None  # For other types of changes, we'll use the default notification format

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

def main():
    """Main entry point for the scraper."""
    try:
        # Log startup information
        logger.info("="*50)
        logger.info("Starting Yad2 Scraper Worker Run")
        verify_worker_run()
        
        # Log environment information
        logger.info(f"Running in container: {os.getenv('CONTAINER_ENV') == 'true'}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Data directory: {get_data_dir()}")
        logger.info(f"Environment variables:")
        for key in ['TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'CONTAINER_ENV']:
            logger.info(f"  {key}: {'✓ Set' if os.getenv(key) else '✗ Not set'}")
        
        # Load environment variables
        load_dotenv()
        
        # Create scraper instance
        scraper = Yad2Scraper()
        
        # Create notifier instance
        notifier = TelegramNotifier()
        
        # Try to send a startup notification
        try:
            startup_msg = "🤖 Yad2 Scraper started successfully!"
            notifier.notify_new_listings_sync([{"custom_message": startup_msg}])
            logger.info("Startup notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {str(e)}")
        
        # Load tracked listings
        tracked_listings = load_tracked_listings()
        logger.info(f"Loaded {len(tracked_listings)} tracked listings")
        
        logger.info("Searching for listings...")
        current_listings = scraper.search_listings()
        
        # Convert current listings to a dictionary for easier comparison
        current_listings_dict = {str(listing['id']): listing for listing in current_listings}
        
        # Find new, updated, and removed listings
        new_listings = []
        updated_listings = []
        removed_listings = []
        price_changes = []  # New list specifically for price changes
        
        # Check for new and updated listings
        for listing_id, listing in current_listings_dict.items():
            if listing_id not in tracked_listings:
                new_listings.append(listing)
                tracked_listings[listing_id] = {
                    'first_seen': datetime.now().isoformat(),
                    'details': listing
                }
            else:
                changed, change_type = is_listing_changed(tracked_listings[listing_id]['details'], listing)
                if changed:
                    if change_type == 'price':
                        price_changes.append((listing_id, tracked_listings[listing_id]['details'], listing))
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
        logger.info(f"Found {len(price_changes)} price changes")
        
        # Check if we should send a daily digest
        if should_send_daily_digest():
            logger.info("Sending daily digest...")
            digest_message = format_daily_digest(tracked_listings)
            notifier.notify_new_listings_sync([{"custom_message": digest_message}])
            save_last_digest_time(datetime.now())
        
        # Send notifications for changes
        notifications = []
        
        # Format new listings
        if new_listings:
            notifications.append("🆕 <b>New Listings:</b>")
            for listing in new_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Format price changes (send these immediately, even if there are no other changes)
        if price_changes:
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("💰 <b>Price Changes:</b>")
            for listing_id, old_listing, new_listing in price_changes:
                notifications.append(format_change_message(listing_id, old_listing, new_listing, 'price'))
        
        # Format other updated listings
        if updated_listings:
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("📝 <b>Updated Listings:</b>")
            for listing in updated_listings:
                if listing not in [new_listing for _, _, new_listing in price_changes]:
                    notifications.append(notifier.format_listing_message(listing))
        
        # Format removed listings
        if removed_listings:
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("❌ <b>Removed Listings:</b>")
            for listing in removed_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Send all notifications as one message
        if notifications:
            notifier.notify_new_listings_sync([{"custom_message": "\n\n".join(notifications)}])
        else:
            logger.info("No changes in listings")
        
        # Save current results to a file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"listings_{timestamp}.json"
        
        with open(get_file_path(filename), 'w', encoding='utf-8') as f:
            json.dump(current_listings, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Results saved to {filename}")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}", exc_info=True)
        # Try to send error notification
        try:
            error_msg = f"⚠️ Yad2 Scraper Error:\n\n{str(e)}"
            notifier.notify_new_listings_sync([{"custom_message": error_msg}])
        except:
            logger.error("Failed to send error notification", exc_info=True)
        raise

def verify_cron_run():
    """Create or update a file to track cron runs."""
    cron_file = os.path.join(get_data_dir(), 'last_cron_run.txt')
    try:
        with open(cron_file, 'w') as f:
            f.write(datetime.now().isoformat())
        logger.info(f"Cron run verified and saved to {cron_file}")
    except Exception as e:
        logger.error(f"Failed to write cron verification file: {str(e)}")

if __name__ == "__main__":
    verify_cron_run()
    main() 