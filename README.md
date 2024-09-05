# CoachGPT

CoachGPT is a Python package that provides APIs to create a chat session and obtain initial analysis, as well as continue the chat session by sending messages.

## Endpoints

There are 2 API endpoints that are exposed:

1. **Creating a Chat Session and Obtaining Initial Analysis:**<br>
   The **/v1/conversations/summary** Creates a chat session and provides initial analysis based on the provided chat messages.

2. **Continuing the Chat Session:**<br>
   To continue the chat session, you can use the **/v1/conversations/query** endpoint. This endpoint accepts a JSON payload containing the new message to be added to the chat session and returns updated analysis based on the new message.

**Swagger Link:** For viewing it on local server, run main.py and then use URL http://127.0.0.1:5000/swagger-summary/

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.6+
- Other dependencies specified in the `requirements.txt` file

## Install dependencies

```bash
pip install -r requirements.txt
```

## Environment variables

1. Create a .env file in the root directory of your project.
2. Add environment-specific variables and their values to it. Refer to the .env.example file for the needed variables.
3. Make sure to add this file to your .gitignore file to keep your environment variables private.

## Run the endpoints on local server

```bash
python main.py
```

## Run the AMQP consumption on local server

```bash
python amqp.py
```

The project will be accessible at http://127.0.0.1:5000/ by default.
