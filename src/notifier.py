import os
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
import re
import httpx
import time
from src.utils import is_excluded

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self):
        """Initialize the notifier with Telegram bot token and chat ID."""
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.token or not self.chat_id:
            logger.warning("Telegram credentials not found in environment variables")
            return
            
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.bot = Bot(token=self.token)
    
    async def send_message(self, message: str) -> bool:
        """
        Send a message via Telegram.
        
        Args:
            message (str): The message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            logger.info(f"Attempting to send message to channel {self.chat_id}")
            response = await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'  # Re-enable HTML parsing for better formatting in channels
            )
            logger.info(f"Message sent successfully: {response.message_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            # If HTML parsing fails, try with simpler HTML
            try:
                logger.info("Retrying with simplified HTML")
                # Keep HTML formatting but simplify the message
                simplified_message = message
                
                # Remove any complex HTML tags, keeping only basic ones
                simplified_message = re.sub(r'<(?!/?(?:b|i|a\s.*?|/a))[^>]*>', '', simplified_message)
                
                response = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=simplified_message,
                    parse_mode='HTML'
                )
                logger.info(f"Simplified HTML message sent successfully: {response.message_id}")
                return True
            except TelegramError as e2:
                logger.error(f"Failed to send simplified HTML message: {str(e2)}")
                return False

    def format_listing_message(self, listing: Dict[str, Any]) -> str:
        """
        Format a listing into a readable Telegram message.
        
        Args:
            listing (dict): The listing data
            
        Returns:
            str: Formatted message
        """
        # Handle custom messages
        if 'custom_message' in listing:
            return listing['custom_message']
            
        try:
            # Format price with commas if it's a number
            price = listing.get('price')
            if isinstance(price, (int, float)):
                price_text = f"₪{price:,}"
            else:
                price_text = "₪N/A"
            
            # Helper function to safely escape HTML
            def escape_html(text):
                if text is None:
                    return ''
                return str(text).replace('<', '&lt;').replace('>', '&gt;')
            
            # Get address components
            address = listing.get('address', {})
            street = escape_html(address.get('street', ''))
            number = escape_html(address.get('number', ''))
            floor = address.get('floor')
            neighborhood = escape_html(address.get('neighborhood', {}).get('text', ''))
            
            # Get details
            details = listing.get('details', {})
            rooms = details.get('rooms')
            square_meters = details.get('square_meters')
            date_added = details.get('date_added')
            updated_at = details.get('updated_at')
            
            # Format dates
            date_text = []
            if date_added:
                try:
                    added_date = datetime.fromisoformat(date_added)
                    date_text.append(f"Added to Yad2: {added_date.strftime('%Y-%m-%d %H:%M')}")
                except (ValueError, TypeError):
                    pass
            if updated_at:
                date_text.append(f"Updated: {updated_at}")
            
            # Build message
            message = [
                f"🏠 <b>{escape_html(listing.get('title', 'New Listing'))}</b>",
                f"💰 Price: {price_text}",
                f"📍 Address: {street} {number}" + (f", Floor {floor}" if floor else ""),
                f"🏘️ Neighborhood: {neighborhood}",
                f"🚪 Rooms: {rooms}" if rooms else None,
                f"📏 Size: {square_meters}m²" if square_meters else None,
                f"🔗 <a href='{listing.get('link')}'>View on Yad2</a>"
            ]
            
            # Add dates if available
            if date_text:
                message.append("\n🕒 " + " | ".join(date_text))
            
            # Filter out None values and join with newlines
            return "\n".join(line for line in message if line is not None)
            
        except Exception as e:
            logger.error(f"Error formatting listing message: {str(e)}")
            return "Error formatting listing"

    async def notify_new_listings(self, listings: List[Dict[str, Any]]) -> None:
        """
        Send notifications for new listings.
        
        Args:
            listings (List[Dict]): List of new listings to notify about
        """
        if not listings:
            return
            
        logger.info(f"Sending notifications for {len(listings)} new listings")
        
        for listing in listings:
            message = self.format_listing_message(listing)
            success = await self.send_message(message)
            if success:
                logger.info(f"Successfully sent notification for listing {listing.get('id')}")
            else:
                logger.error(f"Failed to send notification for listing {listing.get('id')}")
            # Add a small delay between messages to avoid hitting rate limits
            await asyncio.sleep(1)

    def notify_new_listings_sync(self, listings):
        """Send notifications for new listings synchronously."""
        if not self.token or not self.chat_id:
            logger.error("Telegram credentials not found in environment variables")
            return False

        try:
            logger.info(f"Attempting to send {len(listings)} messages")
            success_count = 0
            
            for listing in listings:
                try:
                    if 'custom_message' in listing:
                        message = listing['custom_message']
                    else:
                        message = self.format_listing_message(listing)
                    
                    # Try sending with HTML formatting
                    response = httpx.post(
                        f"{self.base_url}/sendMessage",
                        json={
                            'chat_id': self.chat_id,
                            'text': message,
                            'parse_mode': 'HTML',
                            'disable_web_page_preview': True
                        },
                        timeout=10.0
                    )
                    response.raise_for_status()
                    success_count += 1
                    logger.info(f"Message sent successfully for listing {listing.get('id')}")
                    
                    # Add a small delay between messages to avoid rate limits
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Failed to send message for listing {listing.get('id')}: {str(e)}")
                    continue
            
            logger.info(f"Successfully sent {success_count} out of {len(listings)} messages")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in notify_new_listings_sync: {str(e)}")
            return False

    async def notify_new_listing(self, listing):
        """Send notification for a new listing."""
        message = f"🆕 <b>New Listing:</b>\n\n{self.format_listing_message(listing)}"
        await self.send_message(message)

    async def notify_listing_update(self, new_listing, old_listing):
        """Send notification for an updated listing."""
        message = f"📝 <b>Updated Listing:</b>\n\n{self.format_listing_message(new_listing)}"
        await self.send_message(message)

    async def notify_price_change(self, new_listing, old_listing):
        """Send notification for a price change."""
        old_price = old_listing.get('price', 0)
        new_price = new_listing.get('price', 0)
        change = new_price - old_price
        change_str = f"+{change:,}" if change > 0 else f"{change:,}"
        
        message = [
            f"💰 <b>Price Change:</b>",
            f"Old Price: ₪{old_price:,}",
            f"New Price: ₪{new_price:,}",
            f"Change: ₪{change_str}",
            "",
            self.format_listing_message(new_listing)
        ]
        await self.send_message("\n".join(message))

    async def notify_listing_removed(self, listing):
        """Send notification for a removed listing."""
        listing_id = listing.get('id', 'Unknown')
        address = listing.get('address', {})
        street = address.get('street', '')
        number = address.get('number', '')
        full_address = f"{street} {number}".strip()
        
        message = [
            f"❌ <b>{listing.get('title', 'Listing')}</b> has been removed",
            f"📍 {full_address}" if full_address else None,
            f"🔗 <a href='https://www.yad2.co.il/item/{listing_id}'>View on Yad2</a>",
            ""  # Add blank line between listings
        ]
        await self.send_message("\n".join(line for line in message if line is not None))

    async def send_messages(self, messages):
        """Send multiple messages."""
        logger.info(f"Attempting to send {len(messages)} messages")
        sent_count = 0
        
        for message in messages:
            try:
                if message['type'] == 'new':
                    await self.notify_new_listing(message['listing'])
                elif message['type'] == 'update':
                    await self.notify_listing_update(message['listing'], message['old_listing'])
                elif message['type'] == 'price_change':
                    await self.notify_price_change(message['listing'], message['old_listing'])
                elif message['type'] == 'removed':
                    await self.notify_listing_removed(message['listing'])
                sent_count += 1
                await asyncio.sleep(1)  # Add delay between messages
            except Exception as e:
                logger.error(f"Error sending message: {str(e)}")
                continue
        
        logger.info(f"Successfully sent {sent_count} out of {len(messages)} messages")

    async def send_daily_digest(self, tracked_listings):
        """Send a daily digest of all active listings."""
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
        header = f"📋 <b>Daily Apartments Digest</b>\n\nTotal active listings: {len(listings_with_dates)}\n\n"
        
        # If no listings, send just the header
        if not listings_with_dates:
            await self.send_message(header)
            return
        
        # Format all listings into a single message first
        formatted_listings = []
        for listing_info in listings_with_dates:
            listing = listing_info['details']
            # Check if the listing is excluded
            if is_excluded(listing):
                continue
            first_seen_date = datetime.fromisoformat(listing_info['first_seen']).strftime("%Y-%m-%d %H:%M")
            
            # Format the basic listing message
            listing_msg = self.format_listing_message(listing)
            
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
        
        # Add the last chunk if it has any content
        if current_chunk:
            messages.append("\n\n".join(current_chunk))
        
        # Send each chunk as a separate message
        for i, message in enumerate(messages):
            if len(messages) > 1:
                # Add part number if there are multiple messages
                message = f"📋 <b>Daily Apartments Digest (Part {i+1}/{len(messages)})</b>\n\n{message}"
            await self.send_message(message)
            time.sleep(2)  # Add delay between messages 