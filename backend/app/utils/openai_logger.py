import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)

# Configure logger
logger = logging.getLogger("openai_logger")
logger.setLevel(logging.INFO)

# Create file handler with timestamped filename
file_handler = logging.FileHandler(
    os.path.join(log_dir, f"openai_interactions_{datetime.now().strftime('%Y%m%d')}.log")
)
file_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(message)s')
)
logger.addHandler(file_handler)

def log_openai_interaction(entry_title: str, field_name: str, system_prompt: str, user_prompt: str, response: str) -> None:
    """Log OpenAI API interaction details."""
    log_entry = (
        f"\n{'='*80}\n"
        f"Entry: {entry_title} | Field: {field_name}\n"
        f"System Prompt:\n{system_prompt}\n"
        f"User Prompt:\n{user_prompt}\n"
        f"Response:\n{response}\n"
    )
    logger.info(log_entry)
