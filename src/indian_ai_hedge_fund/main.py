from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from indian_ai_hedge_fund.analysts.warren_buffet import warren_buffett_analyst
from indian_ai_hedge_fund.analysts.ben_graham import ben_graham_analyst
from rich.markdown import Markdown
from rich.console import Console
import questionary
from indian_ai_hedge_fund.prompts.portfolio_review import SYSTEM_PROMPT, HUMAN_PROMPT
import logging
from indian_ai_hedge_fund.tools.zerodha import get_holdings
from pydantic import BaseModel
from typing import List, Dict, Tuple, Callable
from indian_ai_hedge_fund.llm.models import llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Define argument schemas
class GetHoldingsArgs(BaseModel):
    pass  # No arguments needed for get_holdings

class AnalystArgs(BaseModel):
    tickers: List[str]

def get_analysts() -> Dict[str, Tuple[str, Callable]]:
    """Get available analysts with their display names and functions"""
    return {
        'Warren Buffett': ('Warren Buffett', warren_buffett_analyst),
        'Benjamin Graham': ('Benjamin Graham', ben_graham_analyst),
    }

def select_analyst() -> Tuple[str, Callable]:
    """Interactive analyst selection using questionary"""
    analysts = get_analysts()

    # Create choices list
    choices = [
        questionary.Choice(
            title=name,
            value=name
        )
        for name in analysts.keys()
    ]

    # Show selection prompt
    selected = questionary.select(
        "Select your AI analyst",
        choices=choices,
        use_indicator=True,
        style=questionary.Style([
            ('qmark', 'fg:yellow bold'),      # The '?' symbol
            ('question', 'bold'),             # The question text
            ('answer', 'fg:green bold'),      # Selected answer
            ('pointer', 'fg:yellow bold'),    # Selection pointer
            ('highlighted', 'fg:yellow bold') # Highlighted choice
        ])
    ).ask()

    if not selected:
        raise ValueError("No analyst selected")

    return analysts[selected]

def main():
    console = Console()

    try:
        # Get analyst selection
        selected_name, selected_analyst = select_analyst()

        console.print(f"\n[bold green]Selected analyst:[/bold green] {selected_name}\n")

        # Convert analyst name to tool name format
        analyst_name = selected_name.lower().replace(' ', '_')

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
                name=f"{analyst_name}_analyst",
                description=f"Analyzes stocks using {selected_name}'s principles and LLM reasoning. Takes a list of stock tickers as input.",
                func=selected_analyst,
                args_schema=AnalystArgs,
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
        console.print(Markdown(response["output"]))

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red bold]Error:[/red bold] {str(e)}")

if __name__ == "__main__":
    main()
