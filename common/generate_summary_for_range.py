from llama_index.llms import OpenAI
from llama_index import (
    Prompt,
    StorageContext,
    VectorStoreIndex,
    ServiceContext,
)
from dbConfig.constants import (
    daily_summaries_embeddings_table_name,
)
from llama_index.vector_stores.types import (
    MetadataFilters,
    MetadataFilter,
    FilterCondition,
    FilterOperator,
)
from dbConfig.postgres_config import get_daily_summary_count_by_summary_date, get_vector_store, save_message_history


def summary_for_date_range(user_id, week_start_date, week_end_date, session_id):
    weekly_summaries_count = get_daily_summary_count_by_summary_date(
        week_start_date, week_end_date
    )

    row_count = weekly_summaries_count["row_count"]
    weekly_total_calls_count = weekly_summaries_count["weekly_total_calls_count"]
    weekly_successful_calls_count = weekly_summaries_count[
        "weekly_successful_calls_count"
    ]
    weekly_unsuccessful_calls_count = weekly_summaries_count[
        "weekly_unsuccessful_calls_count"
    ]

    template = f"""
        You are a sales coach responsible for providing managerial personnel with a synthesized overview of daily sales calls.

        Information which should be used when generating summary:
            Week start date: {week_start_date}
            Week end date: {week_end_date}
            Total Calls happened in the week: {weekly_total_calls_count}
            Total Successful Calls happened in the week: {weekly_successful_calls_count}
            Total Unsuccessful Calls happened in the week: {weekly_unsuccessful_calls_count}

        Using the call recording transcripts provided and information above, offer a concise summary that encompasses:
            A tally of number of successful vs. unsuccessful follow-up meeting setups.
            Identification of the best and least successful sales representatives.
            Key insights into how sales reps understood and engaged with the prospects.
            Highlighting of any main objections faced and the tactics representatives employed to handle them.
            Short, actionable recommendations to enhance the success rate of scheduling meetings, focusing on areas like opening statements, benefit communication, and closing techniques.
            Notes on the overall tone, professionalism, and technical proficiency exhibited during the calls.
            Remember to maintain a macro-level perspective, avoiding detailed breakdowns of individual calls. Structure your answer in coherent, meaningful paragraphs.
        
        Keep it succinct. When presenting your findings, divide the findings strictly on the basis of separate paragraphs as Team Behaviour, Recommendation and Conclusion, also use the HTML tag <strong></strong> to emphasize these crucial details along with call counts, names, and outcomes. Start these paragraphs from new line, use HTML <br><br> tag for the same
        This will ensure that key data points and takeaways stand out for easy scanning.

        Always return the company/client/representative full names as is without modifying/short forming them. Use full names in all the instances.
    """

    template += """
        Below are the call recording summaries:
        {context_str}
    """
    qa_template = Prompt(template)
    gpt4 = OpenAI(temperature=0, model="gpt-4-1106-preview")

    vector_store = get_vector_store(daily_summaries_embeddings_table_name)

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    service_context_gpt4 = ServiceContext.from_defaults(
        llm=gpt4,
        chunk_size=1024,
    )

    filters = MetadataFilters(
        filters=[
            MetadataFilter(
                key="summary_date", value=week_start_date, operator=FilterOperator.GTE
            ),
            MetadataFilter(
                key="summary_date", value=week_end_date, operator=FilterOperator.LTE
            ),
        ],
        condition=FilterCondition.AND,
    )

    index = VectorStoreIndex.from_documents(
        [], service_context=service_context_gpt4, storage_context=storage_context
    )
    query_engine = index.as_query_engine(
        text_qa_template=qa_template,
        query_mode="compact_accumulate",
        similarity_top_k=row_count,
        filters=filters,
        verbose=True,
    )
    query = "Can you give me a summary about all the calls happened in the week?"
    response = query_engine.query(query)

    save_message_history(query.strip(), "user",
                         user_id, session_id, week_end_date, week_start_date)
    save_message_history(str(response), "system",
                         user_id, session_id, week_end_date, week_start_date)
    print("Successfully saved message history.")

    try:
        summary_details = {
            'summary': str(response),
            'total_calls': weekly_total_calls_count,
            'successful_calls': weekly_successful_calls_count,
            'unsuccessful_calls': weekly_unsuccessful_calls_count
        }
        return summary_details
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "Something goes wrong!"
