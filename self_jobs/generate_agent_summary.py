from llama_index import (
    Prompt,
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context,
)
from llama_index.llms import OpenAI
import os
from dotenv import load_dotenv
from llama_index.vector_stores.types import MetadataFilters, ExactMatchFilter
from llama_index.llms import ChatMessage, MessageRole
from llama_index.prompts.base import ChatPromptTemplate
from llama_index.callbacks import CallbackManager, TokenCountingHandler
import tiktoken
from generate_embeddings import generating_summaries_embeddings
from db_configurations.auto_call_postgres_config import get_vector_store

load_dotenv()

environment = os.environ.get("ENVIRONMENT")


def summary_of_agent(options):
    representative_name = options["representative_name"]
    call_recording_count = options["call_count"]
    row_count = options["row_count"]
    successful_calls_count = options["successful_calls_count"]
    unsuccessful_calls_count = options["unsuccessful_calls_count"]
    summary_date = options["summary_date"]

    token_counter = TokenCountingHandler(
        tokenizer=tiktoken.encoding_for_model("gpt-4-1106-preview").encode
    )

    callback_manager = CallbackManager([token_counter])

    template = f"""Act as if you are a sales data analyst responsible for providing managerial personnel with a synthesized overview of daily sales calls of an agent.

        Using the call recording transcripts provided, offer a concise summary that encompasses:

        Provide below mandatory information in the summary:
            1) Representative Name
            2) Key insights into how sales reps understood and engaged with the prospects in at least 2 lines
            3) Highlighting of any main objections faced and the tactics representatives employed to handle them
            4) Notes on the overall tone, professionalism, and technical proficiency exhibited during the calls in at least 3 lines
            
        Remember to maintain a macro-level perspective, avoiding detailed breakdowns of individual calls. Structure your answer in coherent, meaningful paragraphs.

        Keep it succinct. 

        Example Response JSON Object:
            
            "representativeName": "XYZ PQR",
            "keyInsights": <Key Insights of the call>,
            "objectionHandling": <Objection handing in the call>,
            "otherNotes": <Other notes of the call>

        Below are the call recording transcripts:\n
        {{context_str}}
    """
    summary_prompt = Prompt(template)

    refine_template = f"""
        When refining the answer, you need to refine the textual information using new context if necessary and related:

        You need to update the existing answer with below instructions.

        Refine the existing answer with additional details from new context for below points
            3) Key insights into how sales reps understood and engaged with the prospects in at least 2 lines
            4) Highlighting of any main objections faced and the tactics representatives employed to handle them
            5) Notes on the overall tone, professionalism, and technical proficiency exhibited during the calls in at least 3 lines

        Example Response:

            "representativeName": "XYZ PQR",
            "keyInsights": <Key Insights of the call>,
            "objectionHandling": <Objection handing in the call>,
            "otherNotes": <Other notes of the call>
    """

    CHAT_REFINE_PROMPT_TMPL_MSGS = [
        ChatMessage(
            content=(
                "You are an expert Q&A system that strictly operates in two modes "
                "when refining existing answers:\n"
                "1. **Rewrite** an original answer using the new context. In the new answer, you need to recalculate the numbers if any, and refine the textual information considering the new context\n"
                "2. **Repeat** the original answer if the new context isn't useful.\n"
                f"\n{str(refine_template)}\n"
                "Never reference the original answer or context directly in your answer.\n"
                "Remaining Call Transcripts: {context_msg}\n"
                "Query: {query_str}\n"
                "Original Answer: {existing_answer}\n"
                "New Answer: "
            ),
            role=MessageRole.USER,
        )
    ]

    CHAT_REFINE_PROMPT = ChatPromptTemplate(
        message_templates=CHAT_REFINE_PROMPT_TMPL_MSGS
    )

    filters = MetadataFilters(
        filters=[
            ExactMatchFilter(key="sales_representative_name",
                             value=representative_name),
            ExactMatchFilter(key="date", value=summary_date),
        ]
    )

    vector_store = get_vector_store("call_transcripts")

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    gpt4 = OpenAI(temperature=0, model="gpt-4-1106-preview")
    service_context_gpt4 = ServiceContext.from_defaults(
        llm=gpt4,
        chunk_size=1024,
        callback_manager=callback_manager,
    )
    set_global_service_context(service_context_gpt4)

    index = VectorStoreIndex.from_documents(
        [],
        service_context=service_context_gpt4,
        show_progress=False,
        storage_context=storage_context,
    )
    query_engine = index.as_query_engine(
        text_qa_template=summary_prompt,
        similarity_top_k=row_count,
        verbose=True,
        filters=filters,
        refine_prompt=CHAT_REFINE_PROMPT,
        query_mode="compact_accumulate",
    )

    query = f"Provide me a call summary of representative - {representative_name}."
    response = query_engine.query(query)

    try:
        summary_details = {
            "table_name": "sales_representative_summaries",
            "summary_date": summary_date,
            "representative_name": representative_name,
            "summaries": str(response),
            "total_calls_count": int(call_recording_count),
            "successful_call_count": int(successful_calls_count),
            "unsuccessful_call_count": int(unsuccessful_calls_count),
        }
        generating_summaries_embeddings(summary_details)
        return "Generated sales representative summary successfully!"
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "Something goes wrong!"
