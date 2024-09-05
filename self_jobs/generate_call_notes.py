import os
import json
import pika
import pymssql
import vertexai
from vertexai.generative_models import GenerativeModel, SafetySetting
from dotenv import load_dotenv
import logging
import time
from langchain.text_splitter import CharacterTextSplitter

load_dotenv()
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')

CHUNK_SIZE = 5000
CHUNK_OVERLAP = 50
MODEL = "gemini-1.5-pro-001"
MAX_TOKENS = 512
BATCH_SIZE = 5
FINAL_SUMMARY_LIMIT = 1500
TOKEN_LIMIT = 10000
INITIAL_CONTEXT = """
You will be receiving the transcript of a sales call. The goal is to generate notes summarizing the call's content.
Do not provide any helper text. Skip any sort of text style formatting. 
Correct anything that sounds like "Connected cell" or "Connect and cell" to "ConnectAndSell".
"""

vertexai.init(project=os.getenv('PROJECT_ID'), location=os.getenv('REGION'))
model = GenerativeModel(
    MODEL,
    system_instruction=[INITIAL_CONTEXT]
)

generation_config = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
    ),
]

def log_time(operation):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logging.info(f"{operation} took {elapsed_time:.2f} seconds.")
            return result
        return wrapper
    return decorator

@log_time("Getting database connection")
def get_db_connection():
    logging.info(f".......{os.getenv('SQL_DB_USER')}..........{os.getenv('SQL_DB_HOST')}.........{os.getenv('SQL_DB_NAME')}")
    try:
        server = os.getenv('SQL_DB_HOST')  
        user = os.getenv('SQL_DB_USER')
        password = os.getenv('SQL_DB_PASSWORD')
        database = os.getenv('SQL_DB_NAME')
        conn = pymssql.connect(server, user, password, database)
        logging.info(f"Database connection successful for: {os.getenv('SQL_DB_HOST')} {os.getenv('SQL_DB_USER')} {os.getenv('SQL_DB_NAME')}")
        return conn
    except Exception as e:
        logging.error(f"Unexpected error for: {os.getenv('SQL_DB_HOST')} {os.getenv('SQL_DB_USER')} {os.getenv('SQL_DB_NAME')}: {e}")
        raise

@log_time("Fetching transcript from database")
def fetch_transcript_from_db(lead_transit_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT transcript FROM cas_calltranscript WHERE LeadTransitId = %s", (lead_transit_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    else:
        raise ValueError("Transcript not found for the given lead_transit_id.")

@log_time("Fetching prompt from database")
def fetch_prompt_from_db(company_id):
    conn = get_db_connection()
    cursor = conn.cursor(as_dict=True)
    query = """
        SELECT SettingValue FROM cas_CompanySetting
        WHERE CompanyId = %s AND SettingKey = 'SummaryPrompt'
    """
    cursor.execute(query, (company_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return row['SettingValue']
    else:
        raise ValueError(f"No prompt found for CompanyID: {company_id}")

@log_time("Generating and saving call notes")
def generate_and_save_call_notes(metadata):
    try:
        logging.info(f"Metadata that came: {metadata}")
        lead_transit_id = metadata["lead_transit_id"]
        logging.info(f"Lead Transit ID: {lead_transit_id}")
        content = fetch_transcript_from_db(lead_transit_id)
        prompt = fetch_prompt_from_db(metadata.get("company_id"))
        logging.info(f"Content:::::::::::::::::::::: {len(content) // 3}")
        token_length = len(content) // 3

        if token_length > TOKEN_LIMIT:
            logging.info(f"Transcript length ({token_length} tokens) exceeds {TOKEN_LIMIT} tokens. Chunking the data.")
            chunks = split_text(content)
            summaries = summarize_chunks(chunks, prompt, model)
            combined_summaries = combine_summaries(summaries, prompt, model)
            final_summary_text = final_summary(combined_summaries, prompt, model)
        else:
            logging.info(f"Transcript length ({token_length} tokens) is within the limit. Generating summary directly.")
            final_summary_text = get_ai_response(content, prompt, model)

        logging.info(f"Call Notes: {final_summary_text}")
        save_transcript_summary(str(final_summary_text), metadata)
        message = {
            "notes": final_summary_text,
            "user_id": metadata["user_id"],
            "user_name": metadata["user_name"],
            "lead_transit_id": metadata["lead_transit_id"]
        }
        publish_to_queue(message=message)
        logging.info("Call Notes are saved and published successfully.")
    except Exception as e:
        logging.error(f"Error in generate_and_save_call_notes: {e}")

@log_time("Splitting text into chunks")
def split_text(text, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP):
    splitter = CharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separator="1:",
        length_function=len,
        is_separator_regex=False
    )
    return splitter.split_text(text)

@log_time("Summarizing chunks")
def summarize_chunks(chunks, prompt, model):
    summaries = []
    for chunk in chunks:
        response_text = get_ai_response(chunk, prompt, model)
        summaries.append(response_text)
    return summaries

@log_time("Generating AI response")
def get_ai_response(text, prompt, model):
    system_message = f"{INITIAL_CONTEXT} {prompt}"
    full_prompt = f"{system_message}\n\n{text}"
    response = model.generate_content(full_prompt,
                                    generation_config=generation_config,
                                    safety_settings=safety_settings)
    cleaned_response = response.text.replace("\n", "")
    return cleaned_response

@log_time("Combining summaries")
def combine_summaries(summaries, prompt, model):
    combined_summaries = []
    for i in range(0, len(summaries), BATCH_SIZE):
        batch = "\n\n".join(summaries[i:i + BATCH_SIZE])
        response_text = get_ai_response(batch, prompt, model)
        combined_summaries.append(response_text)
    return combined_summaries

@log_time("Creating final summary")
def final_summary(combined_summaries, prompt, model):
    final_combined_summary = "\n\n".join(combined_summaries)
    if len(final_combined_summary) > FINAL_SUMMARY_LIMIT:
        final_chunks = split_text(final_combined_summary)
    else:
        final_chunks = [final_combined_summary]

    final_summary_parts = []
    for final_chunk in final_chunks:
        response_text = get_ai_response(final_chunk, prompt, model)
        final_summary_parts.append(response_text)

    return "\n\n".join(final_summary_parts)

@log_time("Saving transcript summary to database")
def save_transcript_summary(call_notes, metadata):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        user_id = metadata["user_id"]
        lead_transit_id = metadata["lead_transit_id"]
        notes = str(call_notes)

        select_query = """
        SELECT COUNT(*)
        FROM cas_CallTranscript
        WHERE UserId = %s AND LeadTransitId = %s
        """

        cursor.execute(select_query, (user_id, lead_transit_id))
        record_exists = cursor.fetchone()[0]

        if record_exists:
            logging.info("The record exists")
            update_query = """
            UPDATE cas_CallTranscript
            SET Notes = %s
            WHERE UserId = %s AND LeadTransitId = %s
            """

            cursor.execute(update_query, (notes, user_id, lead_transit_id))
        else:
            raise ValueError("Record with user_id = {} and LeadTransitId = {} does not exist.".format(user_id, lead_transit_id))
        
        conn.commit()
        logging.info("Transcript summary saved successfully.")

    except Exception as e:
        logging.error(f"Unexpected error for: {os.getenv('SQL_DB_HOST')} {os.getenv('SQL_DB_USER')} {os.getenv('SQL_DB_NAME')}: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@log_time("Publishing message to queue")
def publish_to_queue(message):
    try:
        logging.info(f"Publishing the notes to : {os.getenv('RABBITMQ_PUBLISH_QUEUE')} on host: {os.getenv('RABBITMQ_HOST')} {os.getenv('RABBITMQ_USERNAME')}")
        credentials = pika.PlainCredentials(username=os.getenv('RABBITMQ_USERNAME'),
                                            password=os.getenv('RABBITMQ_PASSWORD'))
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.getenv('RABBITMQ_HOST'),
                                      port=os.getenv('RABBITMQ_PORT'),
                                      credentials=credentials,
                                      virtual_host=os.getenv('RABBITMQ_VHOST')))

        channel = connection.channel()
        channel.queue_declare(queue=os.getenv('RABBITMQ_PUBLISH_QUEUE'), durable=True)
        message_json = json.dumps(message)

        channel.basic_publish(exchange=os.getenv('RABBITMQ_PUBLISH_EXCHANGE'),
                              routing_key=os.getenv('RABBITMQ_PUBLISH_ROUTING_KEY'),
                              body=message_json)
        logging.info("Message published to the queue successfully.")

    except pika.exceptions.AMQPError as e:
        logging.error(f"An error occurred while publishing to the queue: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
