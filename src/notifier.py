import os
from telegram import Bot
from telegram.error import TelegramError
import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class TelegramNotifier:
    def __init__(self, token: str = None, chat_id: str = None):
        """
        Initialize the Telegram notifier.
        
        Args:
            token (str): Telegram bot token. If not provided, will try to get from environment variable TELEGRAM_BOT_TOKEN
            chat_id (str): Telegram chat/channel ID. If not provided, will try to get from environment variable TELEGRAM_CHAT_ID.
                          For channels, this should be the channel ID (e.g., -1001234567890)
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("Telegram bot token not provided and TELEGRAM_BOT_TOKEN environment variable not set")
            
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        if not self.chat_id:
            raise ValueError("Telegram chat ID not provided and TELEGRAM_CHAT_ID environment variable not set")
        
        # Ensure the chat_id is a string
        self.chat_id = str(self.chat_id)
        
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
            # If HTML parsing fails, try without it
            try:
                logger.info("Retrying without HTML parsing")
                response = await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode=None
                )
                logger.info(f"Plain text message sent successfully: {response.message_id}")
                return True
            except TelegramError as e2:
                logger.error(f"Failed to send plain text message: {str(e2)}")
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
            
        address = listing.get('address', {})
        details = listing.get('details', {})
        
        message = [
            f"🏠 <b>{listing.get('title', 'New Listing')}</b>",
            f"💰 Price: ₪{listing.get('price', 'N/A'):,}",
            f"📍 {address.get('street', '')} {address.get('number', '')}, {address.get('neighborhood', '')}",
            f"🛋 {details.get('rooms', 'N/A')} rooms, {details.get('square_meters', 'N/A')}m²",
            f"🔗 <a href='{listing.get('link', '')}'>View on Yad2</a>"
        ]
        
        if listing.get('type') == 'agency':
            message.append(f"🏢 {listing.get('agency', 'N/A')}")
            
        return "\n".join(message)

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

    def notify_new_listings_sync(self, listings: List[Dict[str, Any]]) -> None:
        """
        Synchronous wrapper for notify_new_listings.
        
        Args:
            listings (List[Dict]): List of new listings to notify about
        """
        asyncio.run(self.notify_new_listings(listings)) 