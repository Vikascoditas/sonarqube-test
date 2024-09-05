import json
import os
import openai
from dotenv import load_dotenv

from llama_index import ServiceContext
from llama_index.llms import OpenAI
from llama_index.prompts import ChatPromptTemplate
from llama_index.langchain_helpers.agents import (
    IndexToolConfig,
    LlamaIndexTool,
)

from langchain.chat_models import ChatOpenAI
from langchain.agents import Tool
from langchain_experimental.utilities import PythonREPL
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools.render import format_tool_to_openai_function

from common.query_engines.agent_summary_sql_vector import get_agent_summaries_query_engine
from common.query_engines.call_transcript_sql_vector import get_call_transcripts_query_engine
from dbConfig.postgres_config import get_message_history, save_message_history

load_dotenv()  # take environment variables from .env.

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

# openai.api_key = openai_api_key

def answer_followup_question(query, user_id, session_id):
    messages = get_message_history(user_id)
    gpt4 = OpenAI(temperature=0, model="gpt-4-1106-preview")
    service_context_gpt4 = ServiceContext.from_defaults(
        llm=gpt4,
        chunk_size=1024,
    )

    call_transcript_query_engine = get_call_transcripts_query_engine(
        service_context=service_context_gpt4
    )

    agent_summaries_query_engine = get_agent_summaries_query_engine(
        service_context=service_context_gpt4
    )

    call_transcript_tool_config = IndexToolConfig(
        query_engine=call_transcript_query_engine,
        name="Sales_call_transcript_tool",
        description="Sales calls vector query engine for semantic question answering.",
        tool_kwargs={"return_direct": False},
    )
    call_transcript_tool = LlamaIndexTool.from_tool_config(
        call_transcript_tool_config)

    call_summaries_tool_config = IndexToolConfig(
        query_engine=agent_summaries_query_engine,
        name="Sales_call_summaries_tool",
        description="Sales call summaries vector query engine for semantic question answering.",
        tool_kwargs={"return_direct": False},
    )
    call_summaries_tool = LlamaIndexTool.from_tool_config(
        call_summaries_tool_config)

    python_repl = PythonREPL()
    repl_tool = Tool(
        name="python_repl",
        description="A Python shell. Use this to execute python commands. Input should be a valid python command. If you want to see the output of a value, you should print it out with `print(...)`.",
        func=python_repl.run,
    )

    llm = ChatOpenAI(temperature=0, model="gpt-4-1106-preview")
    chat_history = []

    for message in messages:
        if message["message_role"] == "user":
            chat_history.append(HumanMessage(content=str(message["message"])))
        elif message["message_role"] == "system":
            chat_history.append(AIMessage(content=str(message["message"])))

    chat_history = chat_history[::-1]

    tools = [call_transcript_tool, call_summaries_tool, repl_tool]

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are very powerful assistant, but don't know current events",
            ),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    llm_with_tools = llm.bind(
        functions=[format_tool_to_openai_function(t) for t in tools]
    )

    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_function_messages(
                x["intermediate_steps"]
            ),
            "chat_history": lambda x: x["chat_history"],
        }
        | prompt
        | llm_with_tools
        | OpenAIFunctionsAgentOutputParser()
    )

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    response = agent_executor.invoke(
        {"input": query, "chat_history": chat_history}
    )
    output = response["output"]

    save_message_history(str(query), "user", user_id, session_id)
    save_message_history(str(output), "system", user_id, session_id)

    try:
        print("response", output)
        return output
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return "Something goes wrong!"
