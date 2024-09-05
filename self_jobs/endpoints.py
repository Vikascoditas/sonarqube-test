import json
import os
import nest_asyncio
import sys
import time
import logging

from flask import Flask
from dotenv import load_dotenv

# Add parent directory of self_jobs to sys.path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_dir)
from generate_daily_summary import summary_of_day  # Assuming this module exists
from db_configurations.auto_call_postgres_config import get_representative_details  # Assuming this module exists
from generate_agent_summary import summary_of_agent  # Assuming this module exists

load_dotenv()

nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def get_agent_summary(summary_date):
    logger.info(f"Fetching representative details for {summary_date}")
    representatives = get_representative_details(summary_date)

    if representatives:
        logger.info(f"Found {len(representatives)} representatives for {summary_date}")
        for idx, representative in enumerate(representatives):
            options = {
                'representative_name': representative["representative_name"],
                'call_count': representative["call_count"],
                'row_count': representative["row_count"],
                'successful_calls_count': representative["successful_calls_count"],
                'unsuccessful_calls_count': representative["unsuccessful_calls_count"],
                'summary_date': summary_date,
            }
            logger.info(f"Generating summary for representative {representative['representative_name']}")
            summary_of_agent(options)
            time.sleep(60)
        logger.info("Successfully generated sales representatives summaries")
    else:
        logger.warning(f"No representatives found for {summary_date}")

def get_daily_summary(summary_date):
    logger.info(f"Generating daily summary for {summary_date}")
    summary_of_day(summary_date)
    logger.info("Successfully generated daily summary")

