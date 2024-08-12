import re
import sqlite3
from dotenv import load_dotenv
import os
import time

from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from langserve import add_routes
from fastapi import FastAPI, HTTPException, Request

import numpy as np
import faiss
from langchain_huggingface import HuggingFaceEmbeddings


load_dotenv()

#Langsmith Tracking
os.environ['LANGCHAIN_API_KEY']=os.getenv('LANGCHAIN_API_KEY')
os.environ['LANGCHAIN_TRACKING_V2']="true"
os.environ['LANGCHAIN_PROJECT']=os.getenv('LANGCHAIN_PROJECT')
os.environ['GROQ_API_KEY']=os.getenv('GROQ_API_KEY')
os.environ['HF_TOKEN']=os.getenv('HF_TOKEN')
groq_api_key=os.getenv('GROQ_API_KEY')

model=ChatGroq(model='llama3-8b-8192', groq_api_key=groq_api_key)

embedding=HuggingFaceEmbeddings(model_name='all-MiniLM-L6-v2')

store={}

faiss_store = {}

def get_session_history(session_id:str)->BaseChatMessageHistory:
    if session_id not in store:
        store[session_id]=ChatMessageHistory()
    return store[session_id]


# Regex patterns
# 10 digit phone number
PHONE_PATTERN = re.compile(r'\b\d{10}\b')
# 5 digit number followed by 3 uppercase letters
ORDER_ID_PATTERN = re.compile(r'\b\d{5}[A-Z]{3}\b')

def find_phone_number(text: str):
    match = PHONE_PATTERN.search(text)
    return match.group(0) if match else None

def find_order_id(text: str):
    match = ORDER_ID_PATTERN.search(text)
    return match.group(0) if match else None

def query_customer(phone: str):
    conn = sqlite3.connect('walmart.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM customers WHERE phone = ?', (phone,))
    result = cursor.fetchone()
    conn.close()
    return result

def query_order(order_id: str):
    conn = sqlite3.connect('walmart.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM orders WHERE orderId = ?', (order_id,))
    result = cursor.fetchone()
    conn.close()
    return result

# Define a dictionary to store FAISS indices for each session
faiss_indices = {}
faiss_stores = {}

def get_faiss_index(session_id: str):
    if session_id not in faiss_indices:
        dimension = 384  # Dimension of the embeddings
        faiss_indices[session_id] = faiss.IndexFlatL2(dimension)
        faiss_stores[session_id] = {}
    return faiss_indices[session_id], faiss_stores[session_id]


def store_in_faiss(data_tuple, query_type, session_id):
    index, faiss_store = get_faiss_index(session_id)

    if query_type == 'customer':
        text = f"User ID: {data_tuple[0]}, Name: {data_tuple[1]} {data_tuple[2]}, Email: {data_tuple[3]}, Phone: {data_tuple[4]}, Address: {data_tuple[5]}, Registration Date: {data_tuple[6]}"
    elif query_type == 'order':
        text = f"Order ID: {data_tuple[0]}, User ID: {data_tuple[1]}, Order Date: {data_tuple[2]}, Total Amount: {data_tuple[3]}, Status: {data_tuple[4]}, Shipping Address: {data_tuple[5]}"
    else:
        text = data_tuple

    embedding_vector = embedding.embed_query(text)
    embedding_vector = np.array(embedding_vector).reshape(1, -1)
    index.add(embedding_vector)
    faiss_store[text] = embedding_vector
    print(f"Added to FAISS for session {session_id}: {text}")


def search_faiss(query_text, session_id):
    index, _ = get_faiss_index(session_id)

    query_vector = embedding.embed_query(query_text)
    query_vector = np.array(query_vector).reshape(1, -1)

    distances, indices = index.search(query_vector, k=5)

    if indices.size == 0 or indices[0][0] == -1:
        return []

    results = []
    faiss_store = faiss_stores.get(session_id, {})
    for idx in indices[0]:
        if 0 <= idx < len(faiss_store):
            results.append(list(faiss_store.keys())[idx])

    return results




# with_message_history=RunnableWithMessageHistory(model,get_session_history)

config={"configurable":{"session_id" : '{session_id}'}}

# prompt = ChatPromptTemplate(
#     messages=[
#         SystemMessage('''You are a helpful and calm customer support agent, AISHA.
#                       Answer to user queries and provide them with the best possible solution in the language they asked the question.
#                       If you do not have their name and phone number, ask them for it.
#                       If they face a technical issue, tell them some basic troubleshooting steps.
#                       If they have a complaint, ask them for the details and create a ticket for them.
#                       If they want to know about their order, ask them for their order number and provide them with the details.
#                       Don't be too frank and don't answer unrelated questions, if a user asks anything that is not related, 
#                       ask them to ask only related questions politely.
#                       There is a flow to follow in the conversation, follow it and provide the best possible solution to the user.
#                       First, greet the user, then ask them for their name and phone number, then ask them for their query,
#                       then provide them with the solution, if they are not satisfied, then lodge a complaint and raise a ticket. 
#                       And at last, ask them if they have any other queries.
#                       If they have any other queries, ask them to ask them one by one.
#                       '''),
#         MessagesPlaceholder(variable_name="messages")
#     ]
# )

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", '''You are AISHA, a calm and helpful customer support agent. Answer the queries in {language}.
                    Greet users & introduce yourself only in the first message of the session and ask for phone number.
                    Respond to user queries directly, without greetings or unnecessary repetition.
                    DON'T REPEAT THE THINGS YOU HAVE SAID BEFORE.
                    If the user expresses gratitude or says goodbye, acknowledge it politely.
                    If the user's name or phone number is missing, ask for it.
                    For technical issues, provide basic troubleshooting steps.
                    For complaints, request details and create a ticket.
                    Avoid answering unrelated questions and guide users to stay on topic.
                    Do not offer discounts or promotions.
                    Keep it short, if the query is solved, ask if they have any more queries.
                    If user says thank you or goodbye or issue resolved, just end the conversation.
                    If no further queries, end with: "Thank you for contacting us. Have a great day!"
                      '''),
        # ('assistant', 'Hi! My name is AISHA. How can I help you today?'),
        ('system', 'This is the context of user from Database: {faiss_context}'),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

output_parser=StrOutputParser()

chain=prompt|model|output_parser


with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)


# response=with_message_history.invoke(
#     input={"messages": [HumanMessage(content="Hi!")]},
#     config=config,
# )
# response.content

app=FastAPI(title="AISHA", version="1.0.0", description="AISHA API")

# add_routes(
#     app,
#     with_message_history,
#     path='/chat',
# )

@app.post("/chat")
async def invoke_chat(request: Request):
    data = await request.json()

    input_data = data.get("input", {})
    if not input_data:
        return {"response": "Invalid input format. No content found."}

    content = input_data.get("content", "")
    language = input_data.get("language", "en")

    config = data.get("config", {})
    session_id = config.get("session_id", "")
    

    print(f"Received content: {content}")

    phone_number = find_phone_number(content)
    if phone_number:
        customer = query_customer(phone_number)
        if customer:
            store_in_faiss(data_tuple=customer, query_type='customer', session_id=session_id)
        else:
            store_in_faiss(data_tuple=f"Customer with phone number {phone_number} not found", query_type='failed', session_id=session_id)

    order_id = find_order_id(content)
    if order_id:
        order = query_order(order_id)
        if order:
            store_in_faiss(data_tuple=order, query_type='order', session_id=session_id)
        else:
            store_in_faiss(data_tuple=f'Order with orderId {order_id} not found', query_type='failed', session_id=session_id)

    faiss_results = search_faiss(content, session_id)
    faiss_context = " ".join(faiss_results) if faiss_results else "No relevant context found."

    try:
        response = with_message_history.invoke(
            input={
                "input": [HumanMessage(content=content)],
                "faiss_context": faiss_context,
                "language": language
            },
            config={"configurable": {"session_id": session_id}}
        )
    except Exception as e:
        response = str(e)

    return {"response": response}



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='localhost', port=8001)