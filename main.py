import json
import os
import openai
import uuid
import random
import datetime
from flask import Flask, request, jsonify
from common.answer_followup_questions import answer_followup_question
from common.generate_summary_for_range import summary_for_date_range
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import pymssql
import pika

from self_jobs.config_loader import load_and_set_config, update_config_based_on_token

# Load and set configurations
load_and_set_config()
openai_api_key = os.environ.get("OPENAI_API_KEY")
openai.api_key = openai_api_key

app = Flask(__name__)
# Enable CORS for specific route and origin
CORS(app, resources={r"/v1/conversations/*": {"origins": "*"}})


SWAGGER_URL = "/swagger-summary"
API_URL = "/static/swagger.json"

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': 'Access API'
    }
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

# Configuration for the connections
sql_server_config = {
    'server': os.getenv('SQL_DB_HOST') ,
    'user': os.getenv('SQL_DB_USER'),
    'password': os.getenv('SQL_DB_PASSWORD'),
    'database': os.getenv('SQL_DB_NAME')
}

rabbitmq_config = {
    'host': os.getenv('RABBITMQ_HOST'),
    'port': os.getenv('RABBITMQ_PORT'),
    'user': os.getenv('RABBITMQ_USERNAME'),
    'password': os.getenv('RABBITMQ_PASSWORD')
}

@app.route('/v1/conversations/summary', methods=['POST'])
def analyze():
    try:
        # Retrieve the environment_token from the headers
        environment_token = request.headers.get('environment_token')
        if not environment_token:
            return jsonify({'error': 'environment_token header is required'}), 400
        
        data = request.json or {}
        if not data:
            today = datetime.date.today()
            week_start_date = today - datetime.timedelta(days=today.weekday())
            week_end_date = week_start_date + datetime.timedelta(days=4)
            data = {
                'user_id': random.randint(1000, 9999),
                'week_start_date': str(week_start_date),
                'week_end_date': str(week_end_date)
            }
        user_id = data['user_id']
        session_id = uuid.uuid4()

        update_config_based_on_token(environment_token.upper())

        initial_analysis = perform_initial_analysis(user_id, data, session_id)
        return jsonify({'session_id': session_id, 'initial_analysis': initial_analysis})
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred'}), 500


def perform_initial_analysis(user_id, data, session_id):
    week_start_date = data['week_start_date']
    week_end_date = data['week_end_date']
    initial_analysis_result = summary_for_date_range(
        user_id, week_start_date, week_end_date, session_id)
    return initial_analysis_result


@app.route('/v1/conversations/query', methods=['POST'])
def send_message():
    try:
        # Retrieve the environment_token from the headers
        environment_token = request.headers.get('environment_token')
        if not environment_token:
            return jsonify({'error': 'environment_token header is required'}), 400
        
        data = request.json
        if not data:
            return jsonify({'error': 'Request body must be JSON'}), 400

        session_id = data.get('session_id')
        query = data.get("query")
        user_id = data.get("user_id")
        if not session_id or not query or not user_id:
            return jsonify({'error': 'Missing required fields: session_id, query, user_id'}), 400

        update_config_based_on_token(environment_token.upper())

        response_to_query = answer_followup_question(
            query=query, user_id=user_id, session_id=session_id)
        return jsonify({'session_id': session_id, 'response': str(response_to_query)})
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred'}), 500


@app.route('/healthcheck', methods=['GET'])
def healthcheck():
    response = {}

    # Health check for SQL Server
    try:
        conn = pymssql.connect(
            server=sql_server_config['server'],
            user=sql_server_config['user'],
            password=sql_server_config['password'],
            database=sql_server_config['database']
        )
        conn.close()
        response['sqlserver'] = {'status': 'SUCCESS'}
    except Exception as e:
        response['sqlserver'] = {'status': 'FAILURE', 'error': str(e)}

    # Health check for RabbitMQ
    try:
        credentials = pika.PlainCredentials(rabbitmq_config['user'], rabbitmq_config['password'])
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=rabbitmq_config['host'],
            port=rabbitmq_config['port'],
            credentials=credentials,
            virtual_host=os.getenv('RABBITMQ_VHOST', '/')
        ))
        connection.close()
        response['rabbitmq'] = {'status': 'SUCCESS'}
    except Exception as e:
        response['rabbitmq'] = {'status': 'FAILURE', 'error': str(e)}

    status_code = 200 if all(service['status'] == 'SUCCESS' for service in response.values()) else 500
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)
