
from langchain.chat_models import init_chat_model

from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model(model="gpt-4o", model_provider='openai', temperature=0)