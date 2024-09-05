import json
import logging
import os
import sys
from dotenv import load_dotenv
import psycopg2
from llama_index.vector_stores import PGVectorStore
import psycopg2.extras

# Add parent directory of self_jobs to sys.path
project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_dir)

# call it in any place of your program
# before working with UUID objects in PostgreSQL
psycopg2.extras.register_uuid()

load_dotenv()


db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER") 
db_password = os.getenv("DB_PASSWORD")
db_name = os.getenv("DB_NAME")

if (
    db_host != None
    and db_port != None
    and db_user != None
    and db_password != None
    and db_name != None
):
    conn = psycopg2.connect(
        host=db_host, database=db_name, user=db_user, password=db_password, port=db_port
    )
    conn.autocommit = True
else:
    print("Provide valid DB configurations")


def get_vector_store(table_name):
    return PGVectorStore.from_params(
        database=db_name,
        host=db_host,
        password=db_password,
        port=db_port,
        user=db_user,
        table_name=table_name,
        embed_dim=1536,
    )


def get_representative_details(call_date):
    try:
        cursor = conn.cursor()
        successful_call_criteria = (
            str(["Meeting Scheduled"])
            .replace("[", "")
            .replace("]", "")
            .replace('"', "'")
        )

        query = f"""
            select
                count(total_calls) as "call_count",
                sum(total_calls) as row_count,
                sum(case
                    when successful_calls >= 1 then 1
                    else 0
                end) as "successful_calls_count",
                sum(case
                    when unsuccessful_calls >= 1 then 1
                    else 0
                end) as "unsuccessful_calls_count",
                "user_name" as "representative_name",
                "date" as "summary_date"
            from
                (
                    select
                        count(id) as total_calls,
                        sum(case
                            when metadata_->>'call_disposition' in ({successful_call_criteria}) then 1
                            else 0
                        end) as "successful_calls",
                        sum(case
                            when metadata_->>'call_disposition' not in ({successful_call_criteria}) then 1
                            else 0
                        end) as "unsuccessful_calls",
                        metadata_->>'user_name' as "user_name",
                        metadata_->>'call_date' as "call_date",
                        metadata_->>'date' as "date"
                    from
                        data_call_transcripts
                    where
                        TO_CHAR((metadata_->>'date')::timestamp, 'yyyy-mm-dd') = '{call_date}'
                    group by
                        metadata_->>'call_date',
                        metadata_->>'user_name',
                        metadata_->>'date'
                ) as "result"
            group by user_name, "date"
        """
        cursor.execute(query)

        columns = list(cursor.description)
        messages = cursor.fetchall()
        cursor.close()
        results = []
        for row in messages:
            row_dict = {}
            for i, col in enumerate(columns):
                row_dict[col.name] = row[i]
            results.append(row_dict)

        return results
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)


def get_agent_summary_count_by_summary_date(summary_date):
    try:
        cursor = conn.cursor()
        query = f"""
            select
                sum((metadata_->>'total_calls_count')::numeric) as daily_total_calls_count,
                sum((metadata_->>'successful_call_count')::numeric) as daily_successful_call_count,
                sum((metadata_->>'unsuccessful_call_count')::numeric) as daily_unsuccessful_call_count,
                count(id)::numeric as "row_count",
                metadata_->>'summary_date' as summary_date
            from
                data_agent_summaries das
            where
                TO_CHAR((metadata_->>'summary_date')::timestamp, 'yyyy-mm-dd') = '{summary_date}'
            group by summary_date
        """
        cursor.execute(query)

        columns = list(cursor.description)
        messages = cursor.fetchall()
        cursor.close()

        # make dict
        results = {}
        for row in messages:
            for i, col in enumerate(columns):
                results[col.name] = row[i]

        return results
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)


def create_call_summaries_table():
    try:
        cursor = conn.cursor()
        table_creation = """
                CREATE TABLE IF NOT EXISTS call_summaries (
                id SERIAL PRIMARY KEY,
                call_summary TEXT,
                file_name TEXT,
                created_at numeric DEFAULT EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)
            )
        """
        cursor.execute(table_creation)
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)


def save_call_summary(call_summary, file_name):
    try:
        create_call_summaries_table()
        cursor = conn.cursor()
        insert_query = (
            f"""INSERT INTO call_summaries(call_summary, file_name) VALUES(%s, %s);"""
        )
        cursor.execute(
            insert_query,
            (
                call_summary,
                file_name,
            ),
        )
        cursor.close()
        return "Call Summary saved successfully!"
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)
