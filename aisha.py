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
from fastapi import FastAPI




load_dotenv()

#Langsmith Tracking
os.environ['LANGCHAIN_API_KEY']=os.getenv('LANGCHAIN_API_KEY')
os.environ['LANGCHAIN_TRACKING_V2']="true"
os.environ['LANGCHAIN_PROJECT']=os.getenv('LANGCHAIN_PROJECT')
os.environ['GROQ_API_KEY']=os.getenv('GROQ_API_KEY')
groq_api_key=os.getenv('GROQ_API_KEY')

model=ChatGroq(model='llama3-8b-8192', groq_api_key=groq_api_key)

store={}

def get_session_history(session_id:str)->BaseChatMessageHistory:
    if session_id not in store:
        store[session_id]=ChatMessageHistory()
    return store[session_id]

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
        ("system", '''You are a helpful and calm customer support agent, AISHA.
                      Answer to user queries and provide them with the best possible solution in the language they asked the question.
                      And don't respond with "here is my response" kind off thing. Just give the answer directly.
                      If you do not have their name and phone number, ask them for it.
                      If they face a technical issue, tell them some basic troubleshooting steps.
                      If they have a complaint, ask them for the details and create a ticket for them.
                      If they want to know about their order, ask them for their order number and provide them with the details.
                      Don't be too frank and don't answer unrelated questions, if a user asks anything that is not related, 
                      ask them to ask only related questions politely.
                      Greet them at the start of the conversation, not in every response. Also, don't repeat things unless they ask you to.
                      DON'T OFFER THEM ANY DISCOUNTS OR PROMOTIONS OF YOUR OWN ACCORD.
                      There is a flow to follow in the conversation, follow it and provide the best possible solution to the user.
                      First, greet the user, then ask them for their name and phone number, then ask them for their query,
                      then provide them with the solution, if they are not satisfied, then lodge a complaint and raise a ticket. 
                      And at last, ask them if they have any other queries.
                      If they have any other queries, ask them to ask them one by one.
                      If the user says he/she doesn't have any more queries, then end the conversation by saying "Thank you for contacting us. Have a great day!"
                      '''),
        ('assistant', 'Hi! My name is AISHA. How can I help you today?'),
        ("human", "{query}"),
    ]
)

output_parser=StrOutputParser()

chain=prompt|model|output_parser


with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
)


# response=with_message_history.invoke(
#     input={"messages": [HumanMessage(content="Hi!")]},
#     config=config,
# )
# response.content

app=FastAPI(title="AISHA", version="1.0.0", description="AISHA API")

add_routes(
    app,
    with_message_history,
    path='/chat',
)



if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='localhost',port=8000)