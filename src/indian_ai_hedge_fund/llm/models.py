
from langchain.chat_models import init_chat_model

from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model(model="gemini-2.0-flash", model_provider='google_genai', temperature=0)