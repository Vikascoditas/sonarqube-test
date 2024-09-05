import os
from llama_index import (
    StorageContext,
    VectorStoreIndex,
    Prompt,
)
from common.get_google_creds import access_secret_file
from dbConfig.constants import call_transcription_table_name
from llama_index.indices.vector_store import VectorIndexAutoRetriever
from llama_index.vector_stores.types import MetadataInfo, VectorStoreInfo
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.indices.vector_store.retrievers import VectorIndexAutoRetriever
from llama_index.query_engine.retriever_query_engine import RetrieverQueryEngine
from dotenv import load_dotenv
from dbConfig.postgres_config import get_vector_store

load_dotenv()  # take environment variables from .env.

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT") 
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD") 
db_name = os.getenv("DB_NAME")

def get_call_transcripts_query_engine(service_context):
    vector_store = get_vector_store(call_transcription_table_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    vector_index = VectorStoreIndex.from_documents(
        [],
        service_context=service_context,
        show_progress=False,
        storage_context=storage_context,
    )

    vector_store_prompt_template = """
        Act as if you are a sales data analyst responsible for providing managerial personnel with a synthesized overview of daily sales calls of an agent. Act as if you are expert in math calculations and differentiating between successful and unsuccessful calls. In the data you will find parameter called as "call_disposition" which means outcome of the call. Using the call recording transcripts provided, offer an answer.
        Keep it succinct. 

        call_disposition:
            "Meeting Scheduled" - should be treated as successful call
            ANY OTHER call_disposition should be treated as unsuccessful call

        Below are the call transcripts:\n
        {context_str}

        ### 
            IMPORTANT: STRICTLY If there are any math calculation involves in the question then you need to write a valid python code and return that code. Do not return the calculations directly or do not do it on your own. RETURN ONLY THE CODE WITHOUT ANY OTHER THINGS.
            WRITING PYTHON CODE IS NOT TO USED FOR PROVIDING ANSWER TO THE SEMANTIC QUESTION.
        ###
    """
    vector_store_prompt = Prompt(vector_store_prompt_template)

    vector_store_info = VectorStoreInfo(
        content_info="Call transcripts of different representatives",
        metadata_info=[
            MetadataInfo(name="call_date", type="str",
                         description="date & time of call in MM/DD/YYYY HH:M:S AM Format"),
            MetadataInfo(name="date", type="str",
                         description="date of call in YYYY-MM-DD format"),
            MetadataInfo(name="time", type="str",
                         description="time of call in HH:M:S AM Format"),
            MetadataInfo(
                name="company_name",
                type="str",
                description="client/contact company name",
            ),
            MetadataInfo(
                name="contact_first_name",
                type="str",
                description="contact's first name",
            ),
            MetadataInfo(
                name="contact_last_name", type="str", description="contact's last name"
            ),
            MetadataInfo(
                name="contact_country", type="str", description="contact's country"
            ),
            MetadataInfo(
                name="contact_job_industry",
                type="str",
                description="contact's job industry",
            ),
            MetadataInfo(
                name="contact_job_level", type="str", description="contact's job level"
            ),
            MetadataInfo(
                name="contact_job_title", type="str", description="contact's job title"
            ),
            MetadataInfo(
                name="call_disposition", type="str", description="call outcome"
            ),
            MetadataInfo(
                name="sales_representative_name",
                type="str",
                description="sales representative/caller name",
            ),
            MetadataInfo(name="call_talk_time", type="str",
                         description="call talk time in seconds"),
        ],
    )
    vector_auto_retriever = VectorIndexAutoRetriever(
        vector_index, vector_store_info=vector_store_info, similarity_top_k=30
    )

    retriever_query_engine = RetrieverQueryEngine.from_args(
        vector_auto_retriever,
        service_context=service_context,
        text_qa_template=vector_store_prompt,
        response_mode="compact_accumulate",
    )

    return retriever_query_engine
