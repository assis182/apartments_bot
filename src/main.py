import os
from dotenv import load_dotenv
from src.scraper import Yad2Scraper
from src.notifier import TelegramNotifier
import json
from datetime import datetime, timedelta
import logging
import argparse
from src.utils import (
    logger,
    get_data_dir,
    get_file_path,
    load_tracked_listings,
    save_tracked_listings,
    load_last_digest_time,
    save_last_digest_time,
    verify_worker_run,
    verify_cron_run,
    load_exclusions,
    add_to_exclusions,
    remove_from_exclusions,
    is_excluded,
    add_address_to_exclusions,
    add_street_to_exclusions
)
import time
import asyncio
import requests
import glob

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

def manage_exclusions(args):
    """Handle exclusion list management commands."""
    if args.command == 'list':
        exclusions = load_exclusions()
        if not exclusions:
            print("No excluded listings.")
            return
            
        print("\nExcluded Listings:")
        print("="*80)
        
        # Handle both list and dictionary formats
        items = exclusions.values() if isinstance(exclusions, dict) else exclusions
        
        for item in items:
            address = item.get('address', {})
            if item.get('exclude_entire_street'):
                print(f"\nExcluded Street: {address.get('street', 'N/A')}")
            else:
                print(f"\nID: {item['id']}" if item.get('id') else "\nManually excluded address")
                print(f"Address: {address.get('full', 'N/A')}")
            print(f"Excluded at: {item.get('excluded_at', 'N/A')}")
            print(f"Reason: {item.get('reason', 'N/A')}")
            print("-"*40)
            
    elif args.command == 'remove':
        if not args.id and not (args.street and args.number):
            print("Error: Please provide either a listing ID or street and number to remove")
            return
            
        if args.id:
            remove_from_exclusions(args.id)
            print(f"Removed listing {args.id} from exclusions list")
        else:
            full_address = f"{args.street} {args.number}".strip()
            remove_from_exclusions(full_address)
            print(f"Removed address {full_address} from exclusions list")
            
    elif args.command == 'add':
        if args.street and args.number:
            # Add specific address
            add_address_to_exclusions(args.street, args.number, args.reason)
            print(f"Added address {args.street} {args.number} to exclusions list")
        elif args.street and args.entire_street:
            # Add entire street
            add_street_to_exclusions(args.street, args.reason)
            print(f"Added entire street {args.street} to exclusions list")
        elif args.id:
            # Add by listing ID
            tracked_listings = load_tracked_listings()
            listing_id = str(args.id)
            
            if listing_id in tracked_listings:
                listing = tracked_listings[listing_id]['details']
                add_to_exclusions(listing, reason=args.reason or "Manually excluded")
                print(f"Added listing {listing_id} to exclusions list")
            else:
                print(f"Error: Listing {listing_id} not found in tracked listings")
        else:
            print("Error: Please provide either a listing ID or street and number, or use --entire-street with --street")

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
    last_digest_time = load_last_digest_time()
    if not last_digest_time:
        return True
        
    now = datetime.now()
    try:
        last_digest_dt = datetime.fromisoformat(last_digest_time)
    except (TypeError, ValueError):
        # If there's an error parsing the time, assume we should send the digest
        return True
    
    # Check if it's been more than 24 hours OR if it's a new day and after 10 AM
    return ((now - last_digest_dt).total_seconds() >= 24 * 60 * 60 or 
            (now.date() > last_digest_dt.date() and now.hour >= 10))

def is_update_mode():
    """Check if we're in update mode (after daily digest was sent today)."""
    last_digest_time = load_last_digest_time()
    if not last_digest_time:
        return False
        
    now = datetime.now()
    last_digest_dt = datetime.fromisoformat(last_digest_time)
    
    # We're in update mode if we already sent a digest today
    return now.date() == last_digest_dt.date()

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
    
    # Create header message
    header = f"Total active listings: {len(listings_with_dates)}\n\n"
    
    # If no listings, return just the header
    if not listings_with_dates:
        return [header]
    
    # Format all listings into a single message first
    formatted_listings = []
    for listing_info in listings_with_dates:
        listing = listing_info['details']
        first_seen_date = datetime.fromisoformat(listing_info['first_seen']).strftime("%Y-%m-%d %H:%M")
        
        # Format the basic listing message
        listing_msg = notifier.format_listing_message(listing)
        
        # Add first seen date only if Yad2 date is not available
        if not listing.get('details', {}).get('date_added'):
            listing_msg += f"\n🕒 First seen by script: {first_seen_date}"
        listing_msg += "\n" + "-" * 30
        
        formatted_listings.append(listing_msg)
    
    # Now split into chunks of reasonable size (about 2000 characters each)
    # to avoid Telegram's message length limits
    messages = []
    current_chunk = [header]
    current_length = len(header)
    
    for listing in formatted_listings:
        # Check if adding this listing would exceed Telegram's limit
        if current_length + len(listing) > 2000:  # Reduced from 4000 to 2000 for safety
            # Start a new chunk
            messages.append("\n\n".join(current_chunk))
            current_chunk = [listing]
            current_length = len(listing)
        else:
            current_chunk.append(listing)
            current_length += len(listing)
    
    # Add any remaining listings
    if current_chunk:
        messages.append("\n\n".join(current_chunk))
    
    return messages

def format_change_message(listing_id, old_listing, new_listing, change_type, notifier):
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

async def verify_listing_removed(listing_id, url):
    """Verify if a listing is actually removed by checking its URL."""
    try:
        response = requests.get(url, timeout=10)
        # If we get a 404 or the page indicates the listing is removed, then it's truly removed
        if response.status_code == 404:
            return True
        # Check if the page contains text indicating the listing is removed
        if "המודעה לא קיימת" in response.text or "המודעה הוסרה" in response.text:
            return True
        return False
    except Exception as e:
        logger.error(f"Error verifying listing {listing_id}: {str(e)}")
        # If we can't verify, assume it's not removed to avoid false removals
        return False

def cleanup_old_listings_files():
    """Delete all but the most recent listings_*.json file in the data folder."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    listings_files = glob.glob(os.path.join(data_dir, 'listings_*.json'))
    if len(listings_files) > 1:
        # Sort files by modification time (newest first) and remove all but the first one
        listings_files.sort(key=os.path.getmtime, reverse=True)
        for old_file in listings_files[1:]:
            os.remove(old_file)
            logger.info(f"Removed old listings file: {old_file}")

async def main():
    """Main entry point for the scraper."""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Yad2 Apartment Scraper')
    parser.add_argument('--daily-digest', action='store_true', help='Force send daily digest')
    
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Exclusion management commands
    exclusions_parser = subparsers.add_parser('exclusions', help='Manage exclusion list')
    exclusions_parser.add_argument('command', choices=['list', 'remove', 'add'], help='Command to execute')
    exclusions_parser.add_argument('--id', help='Listing ID for add/remove commands')
    exclusions_parser.add_argument('--street', help='Street name for address-based exclusion')
    exclusions_parser.add_argument('--number', help='Street number for address-based exclusion')
    exclusions_parser.add_argument('--reason', help='Reason for excluding the listing')
    exclusions_parser.add_argument('--entire-street', action='store_true', help='Exclude the entire street')
    
    args = parser.parse_args()
    
    # Handle exclusion management commands
    if args.mode == 'exclusions':
        manage_exclusions(args)
        return
        
    # Initialize components
    logger.info("Initializing scraper...")
    scraper = Yad2Scraper()
    logger.info("Scraper initialized")
    
    notifier = TelegramNotifier()
    logger.info("Notifier initialized")
    
    # Load tracked listings
    tracked_listings = load_tracked_listings()
    logger.info(f"Loaded {len(tracked_listings)} tracked listings")
    
    # Search for new listings
    logger.info("Searching for listings...")
    new_listings = scraper.search_listings()
    
    # Check if we should send daily digest first
    if args.daily_digest or should_send_daily_digest():
        logger.info("Sending daily digest...")
        await notifier.send_daily_digest(tracked_listings)
        save_last_digest_time(datetime.now())
        # In daily digest mode, we don't need to send individual notifications
        # Just update the tracked listings
        for listing in new_listings:
            if not is_excluded(listing):
                listing_id = listing['id']
                tracked_listings[listing_id] = {
                    'details': listing,
                    'first_seen': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
        changes = {
            'new': [],
            'updated': [],
            'removed': [],
            'price_changes': []
        }
    else:
        # We're in update mode, only track changes
        changes = {
            'new': [],
            'updated': [],
            'removed': [],
            'price_changes': []
        }
        
        # Track removed listings
        current_ids = set(listing['id'] for listing in new_listings)
        tracked_ids = set(tracked_listings.keys())
        potentially_removed_ids = tracked_ids - current_ids
        
        # Verify each potentially removed listing
        for listing_id in potentially_removed_ids:
            listing = tracked_listings[listing_id]['details']
            url = listing.get('link')
            if url and await verify_listing_removed(listing_id, url):
                changes['removed'].append({
                    'id': listing_id,
                    'details': listing
                })
                del tracked_listings[listing_id]
            else:
                logger.info(f"Listing {listing_id} not found in API but still exists on Yad2, keeping it tracked")
        
        # Process new and updated listings
        for listing in new_listings:
            listing_id = listing['id']
            
            # Debug logging for הירקון 288
            try:
                if listing.get('address', {}).get('street') == 'הירקון' and listing.get('address', {}).get('number') == '288':
                    logger.debug(f"Raw listing data for הירקון 288: {json.dumps(listing, indent=2, ensure_ascii=False)}")
            except Exception as e:
                logger.error(f"Error logging הירקון 288 data: {str(e)}")
            
            # Skip if listing is excluded
            if is_excluded(listing):
                continue
                
            if listing_id not in tracked_listings:
                # New listing
                tracked_listings[listing_id] = {
                    'details': listing,
                    'first_seen': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                changes['new'].append(listing)
            else:
                # Check for updates
                old_listing = tracked_listings[listing_id]['details']
                is_changed, change_type = is_listing_changed(old_listing, listing)
                
                if is_changed:
                    if change_type == 'price':
                        changes['price_changes'].append({
                            'old': old_listing,
                            'new': listing
                        })
                    else:
                        changes['updated'].append({
                            'old': old_listing,
                            'new': listing
                        })
                        
                    tracked_listings[listing_id]['details'] = listing
                    tracked_listings[listing_id]['last_updated'] = datetime.now().isoformat()
    
    # Log changes
    logger.info("Changes detected:")
    logger.info(f"  • {len(changes['new'])} new listings")
    logger.info(f"  • {len(changes['updated'])} updated listings")
    logger.info(f"  • {len(changes['removed'])} removed listings")
    logger.info(f"  • {len(changes['price_changes'])} price changes")
    
    # Send notifications for changes
    logger.info("Sending notifications for changes...")
    messages = []
    
    # New listings
    for listing in changes['new']:
        messages.append({
            'listing': listing,
            'type': 'new'
        })
    
    # Updated listings
    for change in changes['updated']:
        messages.append({
            'listing': change['new'],
            'old_listing': change['old'],
            'type': 'update'
        })
    
    # Price changes
    for change in changes['price_changes']:
        messages.append({
            'listing': change['new'],
            'old_listing': change['old'],
            'type': 'price_change'
        })
    
    # Removed listings
    for removed in changes['removed']:
        messages.append({
            'listing': removed['details'],
            'type': 'removed'
        })
    
    # Send notifications
    if messages:
        await notifier.send_messages(messages)
    
    # Save updated tracked listings
    save_tracked_listings(tracked_listings)
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = get_file_path(f"listings_{timestamp}.json")
    with open(results_file, 'w') as f:
        json.dump(new_listings, f, indent=2, ensure_ascii=False)
    logger.info(f"Results saved to listings_{timestamp}.json")

    # Clean up old listings files
    cleanup_old_listings_files()

if __name__ == "__main__":
    verify_cron_run()
    asyncio.run(main()) 