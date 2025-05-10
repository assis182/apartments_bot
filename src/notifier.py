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
            chat_id (str): Telegram chat ID to send messages to. If not provided, will try to get from environment variable TELEGRAM_CHAT_ID
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.token:
            raise ValueError("Telegram bot token not provided and TELEGRAM_BOT_TOKEN environment variable not set")
            
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        if not self.chat_id:
            raise ValueError("Telegram chat ID not provided and TELEGRAM_CHAT_ID environment variable not set")
        
        logger.debug(f"Initializing TelegramNotifier with chat_id: {self.chat_id}")
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
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=None
            )
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
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
            f"🏠 {listing.get('title', 'New Listing')}",
            f"💰 Price: ₪{listing.get('price', 'N/A'):,}",
            f"📍 {address.get('street', '')} {address.get('number', '')}, {address.get('neighborhood', '')}",
            f"🛋 {details.get('rooms', 'N/A')} rooms, {details.get('square_meters', 'N/A')}m²",
            f"🔗 {listing.get('link', '')}"
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