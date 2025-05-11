import os
from dotenv import load_dotenv
from src.scraper import Yad2Scraper
from src.notifier import TelegramNotifier
import json
from datetime import datetime, timedelta
import logging
from src.utils import (
    logger,
    get_data_dir,
    get_file_path,
    load_tracked_listings,
    save_tracked_listings,
    load_last_digest_time,
    save_last_digest_time,
    verify_worker_run,
    verify_cron_run
)

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
    last_digest = load_last_digest_time()
    
    # If no previous digest, always send
    if not last_digest:
        logger.info("No previous digest found - will send digest")
        return True
    
    now = datetime.now()
    # If it's a new day and it's after 9 AM Israel time (UTC+3)
    israel_hour = (now.hour + 3) % 24  # Convert to Israel time
    should_send = (now.date() > last_digest.date() and israel_hour >= 9)
    
    if should_send:
        logger.info("Will send daily digest - new day and after 9 AM Israel time")
    else:
        logger.info(f"Skipping daily digest - already sent today at {last_digest.strftime('%H:%M')} (Israel time)")
    
    return should_send

def format_daily_digest(tracked_listings, notifier):
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

def main():
    """Main entry point for the scraper."""
    try:
        # Log startup information
        logger.info("="*50)
        logger.info("Starting Yad2 Scraper")
        verify_worker_run()
        
        # Log environment information
        is_container = os.getenv('CONTAINER_ENV') == 'true'
        logger.info(f"Running in container: {is_container}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Data directory: {get_data_dir()}")
        
        # Log environment variables status
        env_vars = {
            'TELEGRAM_TOKEN': '✓ Set' if os.getenv('TELEGRAM_TOKEN') else '✗ Not set',
            'TELEGRAM_CHAT_ID': '✓ Set' if os.getenv('TELEGRAM_CHAT_ID') else '✗ Not set',
            'CONTAINER_ENV': '✓ Set' if os.getenv('CONTAINER_ENV') else '✗ Not set',
            'YAD2_API_URL': os.getenv('YAD2_API_URL', 'https://www.yad2.co.il')
        }
        logger.info("Environment configuration:")
        for key, value in env_vars.items():
            logger.info(f"  {key}: {value}")
        
        # Load environment variables
        load_dotenv()
        
        # Create scraper instance
        scraper = Yad2Scraper()
        logger.info("Scraper initialized")
        
        # Create notifier instance
        notifier = TelegramNotifier()
        logger.info("Notifier initialized")
        
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
        
        # Only process removals if we successfully got listings
        if current_listings:
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
        else:
            logger.warning("No listings found in current search - keeping existing listings")
        
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
            digest_message = format_daily_digest(tracked_listings, notifier)
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
        if removed_listings and current_listings:  # Only show removals if we got listings
            if notifications:  # Add separator if we had previous listings
                notifications.append("\n" + "="*30 + "\n")
            notifications.append("❌ <b>Removed Listings:</b>")
            for listing in removed_listings:
                notifications.append(notifier.format_listing_message(listing))
        
        # Send all notifications as one message
        if notifications:
            logger.info("Sending notifications for changes...")
            notifier.notify_new_listings_sync([{"custom_message": "\n\n".join(notifications)}])
        else:
            logger.info("No changes to notify about")
        
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

if __name__ == "__main__":
    verify_cron_run()
    main() 