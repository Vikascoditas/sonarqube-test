import json
import sys
from llama_index import (
    Prompt,
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context
)
from llama_index.llms import OpenAI
import os
from dotenv import load_dotenv
from llama_index.vector_stores.types import MetadataFilters, ExactMatchFilter
from llama_index.callbacks import CallbackManager, TokenCountingHandler
import tiktoken

# Add parent directory of self_jobs to sys.path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_dir)
from db_configurations.auto_call_postgres_config import get_vector_store
from generate_embeddings import generating_summaries_embeddings
from db_configurations.auto_call_postgres_config import get_agent_summary_count_by_summary_date

load_dotenv()


db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT") 
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD") 
db_name = os.getenv("DB_NAME")


def summary_of_day(summary_date):
    token_counter = TokenCountingHandler(
        tokenizer=tiktoken.encoding_for_model("gpt-4-1106-preview").encode
    )
    callback_manager = CallbackManager([token_counter])

    agent_summary_counts = get_agent_summary_count_by_summary_date(
        summary_date=summary_date
    )

    row_count = agent_summary_counts["row_count"]
    daily_total_calls_count = agent_summary_counts["daily_total_calls_count"]
    daily_successful_call_count = agent_summary_counts["daily_successful_call_count"]
    daily_unsuccessful_call_count = agent_summary_counts["daily_unsuccessful_call_count"]

    summary_template = f"""
        Act as if you are expert in math, statistical calculations. You have strong knowledge of how sales process works and you are very good at differentiating between successful and unsuccessful calls and aggregating the number of unsuccessful as well as successful calls separately. 

        You will have access to the agent level summary. In each one of them you will have successfulCallCount and unsuccessfulCallCount. We have to make sure the numbers get added correctly.
        
        Using the call recording summaries provided, offer a concise summary that encompasses:

            1) Identification of the best sales representatives having most number of successful calls
            2) Identification of the least successful representatives having most number of unsuccessful calls
            3) Key insights into how sales reps understood and engaged with the prospects.
            4) Highlighting of any main objections faced and the tactics representatives employed to handle them.
            5) Notes on the overall tone, professionalism, and technical proficiency exhibited during the calls.
        
        Remember to maintain a macro-level perspective, avoiding detailed breakdowns of individual calls. Structure your answer in coherent, meaningful paragraphs.

        Keep it succinct.

        Example Response JSON Object (Only return this as your response):
            
            "bestPerformer": "xyz pqr",
            "leastPerformer": "qwe sdf",
            "keyInsights": <Key Insights of the call-summaries>,
            "objectionHandling": <Objection handing in the call-summaries>,
            "otherNotes": <Other notes of the call-summaries>
    """

    summary_template += """
        Below are the call recording summaries:
        {context_str}
    """
    summary_prompt = Prompt(summary_template)

    gpt4 = OpenAI(temperature=0, model="gpt-4-1106-preview")

    vector_store = get_vector_store("sales_representative_summaries")

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    service_context_gpt4 = ServiceContext.from_defaults(
        llm=gpt4,
        chunk_size=1024,
        callback_manager=callback_manager,
    )
    set_global_service_context(service_context_gpt4)

    filters = MetadataFilters(
        filters=[
            ExactMatchFilter(key="summary_date", value=summary_date),
        ]
    )

    index = VectorStoreIndex.from_documents(
        [], service_context=service_context_gpt4, storage_context=storage_context
    )

    query_engine_summarization = index.as_query_engine(
        text_qa_template=summary_prompt,
        similarity_top_k=row_count,
        verbose=True,
        filters=filters,
        query_mode="compact_accumulate",
    )

    query = "Provide a concise summary."

    response = query_engine_summarization.query(query)

    try:
        summary_details = {
            "table_name": "daily_summaries",
            "summary_date": summary_date,
            "summaries": str(response),
            "total_calls_count": int(daily_total_calls_count),
            "successful_call_count": int(daily_successful_call_count),
            "unsuccessful_call_count": int(daily_unsuccessful_call_count),
        }
        generating_summaries_embeddings(summary_details)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "Something goes wrong!"
