from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from indian_ai_hedge_fund.analysts.warren_buffet import warren_buffett_analyst
from rich.markdown import Markdown
from rich.console import Console
from indian_ai_hedge_fund.prompts.portfolio_review import SYSTEM_PROMPT, HUMAN_PROMPT
import logging
from indian_ai_hedge_fund.tools.zerodha import get_holdings
from pydantic import BaseModel
from typing import List
from indian_ai_hedge_fund.llm.models import llm
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

# Define argument schemas
class GetHoldingsArgs(BaseModel):
    pass  # No arguments needed for get_holdings

class WarrenBuffettAnalystArgs(BaseModel):
    tickers: List[str]

# holdings = get_holdings()

# tickers = [h["tradingsymbol"] for h in holdings]

# tickers = ["RELIANCE"]
# warren_buffett_analysis = warren_buffett_analyst(tickers)

# Create LangChain tools
tools = [
    StructuredTool(
        name="get_holdings",
        description="Get the user's portfolio holdings from Zerodha",
        func=get_holdings,
        args_schema=GetHoldingsArgs,
        return_direct=False
    ),
    StructuredTool(
        name="warren_buffett_analyst",
        description="Analyzes stocks using Buffett's principles and LLM reasoning. Takes a list of stock tickers as input.",
        func=warren_buffett_analyst,
        args_schema=WarrenBuffettAnalystArgs,
        return_direct=False
    )
]

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", HUMAN_PROMPT),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# Create the LangChain agent
agent = create_openai_tools_agent(
    llm=llm,
    tools=tools,
    prompt=prompt
)

# Create the agent executor
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    max_iterations=50,
    early_stopping_method="force",
    handle_parsing_errors=True
)

# Run the analysis
response = agent_executor.invoke({"input": "analyze my portfolio"})

console = Console()

console.print(Markdown(response["output"]))
