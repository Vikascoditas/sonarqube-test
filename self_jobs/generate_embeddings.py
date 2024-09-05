import os
from datetime import datetime
from pathlib import Path
import logging
from llama_index import StorageContext, VectorStoreIndex
from llama_hub.file.unstructured import UnstructuredReader
from audio_transcribe import audio_Transcriptions
from db_configurations.auto_call_postgres_config import get_vector_store

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def generating_embeddings(filename, call_metadata):
    logger.info(f"Starting generating_embeddings for {filename}")
    file_name = os.path.splitext(os.path.basename(filename))[0]
    file_path = Path(filename)

    try:
        if file_path.exists():
            logger.info(f"File {filename} exists")
            file_size = os.path.getsize(filename)

            if file_size > 0:
                logger.info(f"File {filename} is not empty")
                documents = audio_Transcriptions(filename)
                for detail in documents:
                    current_date_str = call_metadata["call_date"]
                    current_date = datetime.strptime(current_date_str, "%m/%d/%Y %I:%M:%S %p")
                    formatted_date = current_date.strftime("%Y-%m-%d")
                    formatted_time = current_date.strftime("%I:%M:%S %p")

                    detail.metadata.update({
                        "call_date": call_metadata["call_date"],
                        "date": formatted_date,
                        "time": formatted_time,
                        "company_name": call_metadata["company_name"],
                        "contact_first_name": call_metadata["contact_first_name"],
                        "contact_last_name": call_metadata["contact_last_name"],
                        "contact_country": call_metadata["contact_country"],
                        "contact_job_industry": call_metadata["contact_job_industry"],
                        "contact_job_level": call_metadata["contact_job_level"],
                        "contact_status": call_metadata["contact_status"],
                        "call_disposition": call_metadata["call_disposition"],
                        "sales_representative_name": call_metadata["user_name"],
                        "list_name": call_metadata["list_name"],
                        "contact_job_title": call_metadata["contact_job_title"],
                        "call_talk_time": f"{call_metadata['call_talk_time']} Seconds",
                        "file_name": filename
                    })

                vector_store = get_vector_store("call_transcripts")
                storage_context = StorageContext.from_defaults(vector_store=vector_store)
                index = VectorStoreIndex.from_documents(documents, storage_context=storage_context)
                logger.info(f"Successfully generated embeddings for {filename}")
                return documents
            else:
                logger.warning(f"File {filename} is empty")
                return None
        else:
            logger.error(f"File {filename} does not exist")
            return None
    except Exception as e:
        logger.error(f"Error in generating_embeddings for {filename}: {e}", exc_info=True)
        return None

def generating_summaries_embeddings(summary_details):
    logger.info(f"Starting generating_summaries_embeddings")
    table_name = summary_details["table_name"]
    summary_date = summary_details["summary_date"]
    representative_name = summary_details.get("representative_name", "NOT_FOUND")
    summaries = summary_details["summaries"]
    total_calls_count = summary_details["total_calls_count"]
    successful_call_count = summary_details["successful_call_count"]
    unsuccessful_call_count = summary_details["unsuccessful_call_count"]
    file_name = f"{representative_name}_{summary_date}.txt"

    try:
        with open(file_name, "w") as file:
            file.write(summaries)

        loader = UnstructuredReader()
        documents = loader.load_data(file=Path(file_name))

        for doc in documents:
            doc.metadata.update({
                "summary_date": summary_date,
                "total_calls_count": total_calls_count,
                "successful_call_count": successful_call_count,
                "unsuccessful_call_count": unsuccessful_call_count
            })

            if table_name == "sales_representative_summaries":
                doc.metadata["representative_name"] = representative_name

        vector_store = get_vector_store(table_name)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        os.remove(file_name)
        
        logger.info(f"Successfully generated summaries embeddings and removed {file_name}")
    except Exception as e:
        logger.error(f"Error in generating_summaries_embeddings: {e}", exc_info=True)
