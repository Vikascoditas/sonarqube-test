import logging
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from llama_index.vector_stores import PGVectorStore


psycopg2.extras.register_uuid()

load_dotenv()

db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")
db_user = os.getenv("DB_USER") 
db_password = os.getenv("DB_PASSWORD") 
db_name = os.getenv("DB_NAME")

if (db_host != None and db_port != None and db_user != None
        and db_password != None and db_name != None):
    conn = psycopg2.connect(host=db_host,
                            database=db_name,
                            user=db_user,
                            password=db_password,
                            port=db_port)
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


def get_daily_summary_count_by_summary_date(week_start_date, week_end_date):
    try:
        cursor = conn.cursor()
        query = f"""
            select
                sum(daily_total_calls_count) as weekly_total_calls_count,
                sum(daily_successful_call_count) as weekly_successful_calls_count,
                sum(daily_unsuccessful_call_count) as weekly_unsuccessful_calls_count,
                count(row_count) as row_count
            from
                (
                select
                    sum((metadata_->>'total_calls_count')::numeric) as daily_total_calls_count,
                    sum((metadata_->>'successful_call_count')::numeric) as daily_successful_call_count,
                    sum((metadata_->>'unsuccessful_call_count')::numeric) as daily_unsuccessful_call_count,
                    count(id)::numeric as "row_count",
                    metadata_->>'summary_date' as summary_date
                from
                    data_daily_summaries das
                where
                    TO_CHAR((metadata_->>'summary_date')::timestamp,
                    'yyyy-mm-dd') between '{week_start_date}' and '{week_end_date}'
                group by
                    summary_date
                ) as "result"
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


def create_message_history_table():
    try:
        cursor = conn.cursor()
        table_creation = """
            CREATE TABLE IF NOT EXISTS message_history (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                message_role TEXT NOT NULL,
                user_id numeric,
                session_id uuid,
                created_at numeric DEFAULT EXTRACT(EPOCH FROM CURRENT_TIMESTAMP),
                week_start_date DATE,
                week_end_date DATE
            )
        """
        cursor.execute(table_creation)
        cursor.close()
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)


def save_message_history(message,
                         message_role,
                         user_id,
                         session_id,
                         week_end_date=None,
                         week_start_date=None):
    try:
        create_message_history_table()
        cursor = conn.cursor()

        if week_start_date is None:
            week_start_date = None
        if week_end_date is None:
            week_end_date = None

        insert_query = f"""INSERT INTO message_history(message, message_role, user_id, session_id, week_end_date, week_start_date) VALUES(%s, %s, %s, %s, %s, %s);"""
        cursor.execute(insert_query,
                       (message, message_role, user_id, session_id,
                        week_end_date, week_start_date))
        cursor.close()
        return "Message saved successfully!"
    except (Exception, psycopg2.DatabaseError) as e:
        logging.error(e)
        cursor.close()
        exit(1)


def get_message_history(user_id):
    try:
        create_message_history_table()
        cursor = conn.cursor()
        messages_query = f"""SELECT message, message_role, created_at from message_history WHERE user_id = '{user_id}' order by created_at desc limit 4"""
        cursor.execute(messages_query)

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
