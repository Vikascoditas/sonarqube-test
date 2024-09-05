import os
import logging
from google.cloud import secretmanager
from google.api_core.exceptions import PermissionDenied

logging.basicConfig(level=logging.INFO)  

def access_secret_file():
    try:
        project_id = os.getenv("project_id")
        env_value = os.getenv("env")
        service_name = ""
        if env_value is not None:
            service_name = f"transcript-service-{env_value}"
        else:
            logging.error("Environment variable 'env' is not set.")
            return None
        client = secretmanager.SecretManagerServiceClient()
        secret_name = client.secret_path(project_id, service_name)
        seret_object = client.get_secret(request={"name": secret_name})
        secret_id=seret_object.name
        secret_name = f"{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode("UTF-8")
    except PermissionDenied:
        logging.error("Permission denied while accessing secret.")
        return None
    except Exception as e:
        logging.exception("An error occurred: %s", e)
        return "Something goes wrong!"   
    