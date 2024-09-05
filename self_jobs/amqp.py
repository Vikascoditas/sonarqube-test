import os
import json
import sys
import openai
import shutil
import pika
import logging
import time
from dotenv import load_dotenv
from google.cloud import storage
from datetime import datetime, timedelta
from threading import Thread
from config_loader import load_and_set_config, update_config_based_on_token

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load and set configurations
load_and_set_config()

# Define the heartbeat interval using timedelta
heartbeat_interval = timedelta(seconds=30).total_seconds()

# Add parent directory of self_jobs to sys.path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_dir)

from generate_embeddings import generating_embeddings
from generate_recordings_summary import generating_summary_of_each_recordings
from endpoints import get_agent_summary, get_daily_summary
from generate_call_notes import generate_and_save_call_notes

current_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp3", "wav", "ogg", "txt"}

def connect_to_rabbitmq(host, port, user, password, vhost, heartbeat_interval):
    credentials = pika.PlainCredentials(username=user, password=password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            port=port,
            credentials=credentials,
            virtual_host=vhost,
            connection_attempts=3,  # Retry connection attempts
            retry_delay=5,  # Wait 5 seconds before retrying connection
            heartbeat=int(heartbeat_interval),  # Heartbeat interval in seconds
            blocked_connection_timeout=300,  # Timeout for blocked connection
            socket_timeout=5,  # Socket timeout
        )
    )
    return connection

def process_data_and_store(ch, method, properties, body):
    data = body.decode("utf-8")
    parsed_data = None
    try:
        # Step 1: Parse JSON data
        parsed_data = json.loads(data)
        logger.info("Received message: %s", parsed_data)

        # Step 2: Extract and validate environment token
        environment_token = parsed_data.get("environment_token")
        if environment_token:
            environment_token = environment_token.upper()
            logger.info(f"Environment Token sending for updation: {environment_token}")
            update_config_based_on_token(environment_token)
        if not environment_token:
            logger.error("No environment_token found in the message")
            return

        # Step 3: Process the message based on message_type
        message_type = parsed_data.get("message_type")
        if message_type == "summary":
            current_date_str = parsed_data.get("call_date")
            current_date = datetime.strptime(current_date_str, "%m/%d/%Y %I:%M:%S %p")
            formatted_date = current_date.strftime("%Y-%m-%d")
            get_agent_summary(formatted_date)
            get_daily_summary(formatted_date)
            logger.info("Summaries generated for date: %s", formatted_date)

        elif message_type == "call_notes":
            generate_and_save_call_notes(parsed_data)

        elif message_type == "transcript":
            file_name = parsed_data.get("file_name")
            destination_path = download_file_from_gcp(file_name)
            generate_recording_summary(file_name, destination_path, parsed_data)
            logger.info("Data processed and file downloaded: %s", file_name)
            shutil.rmtree(UPLOAD_FOLDER)
            logger.info("Uploads folder cleaned up")

        else:
            logger.warning("No action to be performed on this message type: %s", message_type)

        # Acknowledge the message only if processing succeeds
        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Message acknowledged")

    except json.JSONDecodeError as e:
        logger.error("Message not acknowledged due to JSON parsing error. Error parsing JSON: %s", e)

    except KeyError as e:
        logger.error("Message not acknowledged due to missing configuration. Configuration error: %s", e)

    except Exception as e:
        logger.error("Error processing message: %s", e, exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag)
        logger.info("Message not acknowledged due to error")

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def download_file_from_gcp(file_name):
    client = storage.Client(project=os.getenv("GCP_PROJECT_ID"))
    bucket = client.get_bucket(os.getenv("GCP_BUCKET_NAME"))
    if allowed_file(file_name):
        blob = bucket.blob(file_name)
        destination_path = os.path.join(UPLOAD_FOLDER, file_name)

        # Create the uploads folder if it doesn't exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
            logger.info("Uploads folder created")

        blob.download_to_filename(destination_path)
        logger.info("File downloaded to: %s", destination_path)
        return destination_path

def generate_recording_summary(file_name, destination_path, metadata):
    fileDate = os.path.basename(file_name)
    filenameWithDate = fileDate[:10]
    documents = generating_embeddings(destination_path, metadata)
    summary = generating_summary_of_each_recordings(documents, filenameWithDate)
    logger.info("Call transcripts & embeddings generated and saved to database: %s", summary)
    # Delete the uploads folder and its contents after processing
    shutil.rmtree(UPLOAD_FOLDER)
    logger.info("Uploads folder cleaned up after processing")

def start_consuming_for_host(host, port, user, password, vhost):
    while True:
        try:
            os.environ["RABBITMQ_HOST"] = host
            os.environ["RABBITMQ_PORT"] = port
            os.environ["RABBITMQ_USERNAME"] = user
            os.environ["RABBITMQ_PASSWORD"] = password
            os.environ["RABBITMQ_VHOST"] = vhost
            connection = connect_to_rabbitmq(
                host, 
                port, 
                user, 
                password, 
                vhost,
                heartbeat_interval
            )
            channel = connection.channel()
            channel.exchange_declare(exchange=os.getenv("RABBITMQ_EXCHANGE"), durable=True)
            channel.queue_declare(queue=os.getenv("RABBITMQ_QUEUE"), durable=True)
            channel.queue_bind(
                exchange=os.getenv("RABBITMQ_EXCHANGE"), 
                queue=os.getenv("RABBITMQ_QUEUE"), 
                routing_key=os.getenv("RABBITMQ_ROUTING_KEY")
            )
            logger.info("RabbitMQ setup completed with exchange %s, queue %s for host %s", os.getenv("RABBITMQ_EXCHANGE"), os.getenv("RABBITMQ_QUEUE"), host)

            # Setup RabbitMQ consumer
            channel.basic_consume(
                queue=os.getenv("RABBITMQ_QUEUE"), on_message_callback=process_data_and_store, auto_ack=False
            )

            logger.info("Waiting for messages on host %s. To exit press CTRL+C", host)
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as e:
            logger.error("AMQP Connection error for host %s: %s", host, e)
            logger.info("Attempting to reconnect in 5 seconds for host %s...", host)
            time.sleep(5)

        except pika.exceptions.ConnectionClosed as e:
            logger.error("Connection closed for host %s: %s", host, e)
            logger.info("Attempting to reconnect in 5 seconds for host %s...", host)
            time.sleep(5)

        except Exception as e:
            logger.error("Unexpected error for host %s: %s", host, e, exc_info=True)
            logger.info("Attempting to reconnect in 5 seconds for host %s...", host)
            time.sleep(5)

        logger.info("RabbitMQ consumer is still running and actively consuming messages for host %s", host)

def start_consuming():
    rabbitmq_hosts = json.loads(os.getenv("RABBITMQ_HOSTS"))
    print("RabbitMQ HOSTS:::::::::::::::::::", rabbitmq_hosts)
    threads = []
    for host_config in rabbitmq_hosts:
        host = host_config["host"]
        port = host_config["port"]
        user = host_config["name"]
        password = host_config["password"]
        vhost = host_config["vhost"]
        thread = Thread(target=start_consuming_for_host, args=(host, port, user, password, vhost))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    start_consuming()
