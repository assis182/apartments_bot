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
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        
        # Remove any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add our handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(cron_handler)
        
        logger = logging.getLogger(__name__)
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
            return datetime.fromisoformat(f.read().strip())
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

# Initialize logger
logger = setup_logging() 