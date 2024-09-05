import os
from dotenv import load_dotenv
from dbConfig.postgres_config import get_vector_store
from dbConfig.constants import agent_summaries_embeddings_table_name
from llama_index import (
    StorageContext,
    VectorStoreIndex,
    Prompt,
)
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.indices.vector_store import VectorIndexAutoRetriever
from llama_index.vector_stores.types import MetadataInfo, VectorStoreInfo
from llama_index.indices.vector_store.retrievers import VectorIndexAutoRetriever
from llama_index.query_engine.retriever_query_engine import RetrieverQueryEngine

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT") 
db_user = os.getenv("DB_USER") 
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

def get_agent_summaries_query_engine(service_context):
    vector_store = get_vector_store(agent_summaries_embeddings_table_name)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    vector_index = VectorStoreIndex.from_documents(
        [],
        service_context=service_context,
        show_progress=False,
        storage_context=storage_context,
    )

    vector_store_prompt_template = """
        You are an sales coach who help managerial people with the overview of the calls happened in the week.
        Please provide answer only using information provided in the context,
        including the total number of successful/unsuccessful follow-up meeting setups.
        Try to understand if any objections were there and how those were handled by the representatives which can be used later while giving the answers

        Below are the call summaries:
        {context_str}

        Try to be very focused while giving your answer, keep it succinct. Try not to provide details of individual calls.
        Always return the company/client/representative full names as is without modifying/short forming them. Use full names in all the instances.

        Provide the answer in meaningful paragraphs if necessary.

        ### 
            IMPORTANT: STRICTLY If there are any math calculation involves in the question then you need to write a valid python code and return that code. Do not return the calculations directly or do not do it on your own. RETURN ONLY THE CODE WITHOUT ANY OTHER THINGS.
            WRITING PYTHON CODE IS NOT TO USED FOR PROVIDING ANSWER TO THE SEMANTIC QUESTION.
        ###
        
        answer the question: {query_str}\n
    """
    vector_store_prompt = Prompt(vector_store_prompt_template)

    vector_store_info = VectorStoreInfo(
        content_info="Call summaries of different sales representatives",
        metadata_info=[
            MetadataInfo(
                name="summary_date", type="str", description="date of call summary with YYYY-MM-DD format"
            ),
            MetadataInfo(
                name="representative_name",
                type="str",
                description="sales representative name",
            ),
            MetadataInfo(
                name="total_calls_count",
                type="integer",
                description="overall sales calls count",
            ),
            MetadataInfo(
                name="successful_call_count",
                type="integer",
                description="overall successful sales calls count",
            ),
            MetadataInfo(
                name="unsuccessful_call_count",
                type="integer",
                description="overall unsuccessful sales calls count",
            ),
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
