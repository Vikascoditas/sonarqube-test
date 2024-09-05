import os
import logging
from llama_index.llms import OpenAI
from llama_index import ServiceContext
from llama_index.composability.joint_qa_summary import QASummaryQueryEngineBuilder
from db_configurations.auto_call_postgres_config import save_call_summary

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

def generating_summary_of_each_recordings(documents, filenameWithDate):
    try:
        logger.info("Starting summary generation for recordings")
        gpt_data = OpenAI(temperature=0, model="gpt-3.5-turbo")
        service_context_gpt_data = ServiceContext.from_defaults(
            llm=gpt_data, chunk_size=4096
        )
        chatgpt = OpenAI(temperature=0, model="gpt-3.5-turbo")
        ServiceContext.from_defaults(llm=chatgpt, chunk_size=4096)
        query_engine_builder = QASummaryQueryEngineBuilder(
            service_context=service_context_gpt_data
        )
        query_engine = query_engine_builder.build_from_documents(documents)
        response = query_engine.query(
            """
                Can you give me a call summary? 

                Summary: <call-summary>

                Also have the metadata information included in the summary in the below format:

                Metadata:
                    List Name,
                    User Name,
                    Company Name,
                    Contact First Name,
                    Contact Last Name,
                    Contact Job Industry,
                    Contact Job Title,
                    Contact Job Level,
                    Contact Country,
                    Contact Status,
                    Call Disposition,
                    Call Talk Time,
                    Call Date
            """,
        )
    except Exception as e:
        logger.error("Error during summary generation", exc_info=True)
        return

    try:
        save_call_summary(str(response), str(documents[0].metadata['file_name']))
        logger.info("Call summary saved successfully")
    except Exception as e:
        logger.error("Error saving call summary", exc_info=True)

    try:
        directory = "summaries/daily_summaries"
        file_name = filenameWithDate
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, file_name)

        with open(file_path, "a") as file:
            file.write(str(response) + "\n\n")
            logger.info(f"Appended to file: {file_path}")
        file.close()
    except FileNotFoundError:
        try:
            with open(file_path, "w") as file:
                file.write(str(response) + "\n\n")
                logger.info(f"Created and wrote to file: {file_path}")
            file.close()
        except Exception as e:
            logger.error(f"Error writing to new file: {file_path}", exc_info=True)
    except Exception as e:
        logger.error(f"Error appending to file: {file_path}", exc_info=True)
        file.close()
