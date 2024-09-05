import os
import json
import re
import sys
import logging
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common.get_google_creds import access_secret_file
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
current_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(root_dir, ".env")
load_dotenv(dotenv_path)

# Load secrets from Secret Manager
secrets_data = access_secret_file()

def load_and_set_config():
    if not secrets_data:
        logger.error("No secrets data found")
        return

    secrets = json.loads(secrets_data)
    environment = secrets.get("ENVIRONMENT")
    if environment not in {"prod", "dev", "test"}:
        logger.error("Invalid or missing environment in secrets")
        return
    os.environ["REGION"] = secrets.get("REGION")
    os.environ["PROJECT_ID"] = secrets.get("PROJECT_ID")
    os.environ["OPENAI_API_KEY"] = secrets.get("OPENAI_API_KEY")
    os.environ["GROQ_API_KEY"] = secrets.get("GROQ_API_KEY")
    os.environ["RABBITMQ_QUEUE"] = secrets.get("RABBITMQ_QUEUE")
    os.environ["RABBITMQ_EXCHANGE"] = secrets.get("RABBITMQ_EXCHANGE")
    os.environ["RABBITMQ_ROUTING_KEY"] = secrets.get("RABBITMQ_ROUTING_KEY")
    os.environ["RABBITMQ_PUBLISH_QUEUE"] = secrets.get("RABBITMQ_PUBLISH_QUEUE")
    os.environ["RABBITMQ_PUBLISH_EXCHANGE"] = secrets.get("RABBITMQ_PUBLISH_EXCHANGE")
    os.environ["RABBITMQ_PUBLISH_ROUTING_KEY"] = secrets.get("RABBITMQ_PUBLISH_ROUTING_KEY")

    logger.info("Environment set to %s", environment)
    logger.info("Database configuration loaded")

    rabbitmq_hosts = []
    val = ''
    env = ''
    for key, value in secrets.items():
        match = re.match(r"RABBITMQ_HOST_(.*)", key)
        if match:
            env = match.group(1)
            host_key = f"RABBITMQ_HOST_{env}"
            port_key = f"RABBITMQ_PORT_{env}"
            name_key = f"RABBITMQ_USERNAME_{env}"
            password_key = f"RABBITMQ_PASSWORD_{env}"
            vhost_key = f"RABBITMQ_VHOST_{env}"

            if host_key in secrets and port_key in secrets:
                rabbitmq_hosts.append({
                    "host": secrets[host_key],
                    "port": secrets[port_key],
                    "name":secrets[name_key],
                    "password":secrets[password_key],
                    "vhost":secrets[vhost_key]
                })
            val = env
    os.environ["RABBITMQ_HOSTS"] = json.dumps(rabbitmq_hosts)
    update_config_based_on_token(val)


def update_config_based_on_token(environment_token):
    logger.info(f"Updating the config with the environment token: {environment_token}")
    secrets = json.loads(secrets_data)
    
    def set_env_var(key, value):
        if value is not None:
            os.environ[key] = value
        else:
            logger.error(f"Missing value for {key} with environment_token {environment_token}")
            return

    try:
        set_env_var("DB_HOST", secrets.get(f"DB_HOST_{environment_token}"))
        set_env_var("DB_PORT", secrets.get(f"DB_PORT_{environment_token}"))
        set_env_var("DB_USER", secrets.get(f"DB_USER_{environment_token}"))
        set_env_var("DB_PASSWORD", secrets.get(f"DB_PASSWORD_{environment_token}"))
        set_env_var("DB_NAME", secrets.get(f"DB_NAME_{environment_token}"))

        set_env_var("SQL_DB_HOST", secrets.get(f"SQL_DB_HOST_{environment_token}"))
        set_env_var("SQL_DB_USER", secrets.get(f"SQL_DB_USER_{environment_token}"))
        set_env_var("SQL_DB_PASSWORD", secrets.get(f"SQL_DB_PASSWORD_{environment_token}"))
        set_env_var("SQL_DB_NAME", secrets.get(f"SQL_DB_NAME_{environment_token}"))

        set_env_var("RABBITMQ_HOST", secrets.get(f"RABBITMQ_HOST_{environment_token}"))
        set_env_var("RABBITMQ_PORT", secrets.get(f"RABBITMQ_PORT_{environment_token}"))
        set_env_var("RABBITMQ_USERNAME", secrets.get(f"RABBITMQ_USERNAME_{environment_token}"))
        set_env_var("RABBITMQ_PASSWORD", secrets.get(f"RABBITMQ_PASSWORD_{environment_token}"))
        set_env_var("RABBITMQ_VHOST", secrets.get(f"RABBITMQ_VHOST_{environment_token}"))

        set_env_var("GCP_PROJECT_ID", secrets.get(f"GCP_PROJECT_ID_{environment_token}"))
        set_env_var("GCP_BUCKET_NAME", secrets.get(f"GCP_BUCKET_NAME_{environment_token}"))
    except ValueError as e:
        logger.error("Error setting environment variables: %s", e)
        raise
    except KeyError as e:
        logger.error("Missing configuration for environment_token %s: %s", environment_token, e)
        raise