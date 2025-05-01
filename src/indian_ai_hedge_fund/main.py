from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
from indian_ai_hedge_fund.analysts.warren_buffet import warren_buffett_analyst
from indian_ai_hedge_fund.analysts.ben_graham import ben_graham_analyst
from rich.markdown import Markdown
from rich.console import Console
import questionary
from indian_ai_hedge_fund.prompts.portfolio_review import SYSTEM_PROMPT, HUMAN_PROMPT
from indian_ai_hedge_fund.tools.zerodha import get_holdings
from pydantic import BaseModel
from typing import List, Dict, Tuple, Callable
from indian_ai_hedge_fund.llm.models import llm
from indian_ai_hedge_fund.utils.logging_config import logger
from indian_ai_hedge_fund.utils.progress import progress
import traceback
from functools import wraps

# Define argument schemas
class GetHoldingsArgs(BaseModel):
    pass  # No arguments needed for get_holdings

class AnalystArgs(BaseModel):
    tickers: List[str]

def wrap_with_progress(func: Callable, agent_name: str) -> Callable:
    """Wrap a function with progress tracking updates."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        current_ticker = None
        status_prefix = "Executing tool"
        # Check if it's an analyst function to extract ticker for better status
        if "_analyst" in func.__name__ and args:
            if isinstance(args[0], list) and args[0]: # Check if first arg is a list of tickers
                 # Can't easily show individual tickers here, just the count
                 status_prefix = f"Analyzing {len(args[0])} stocks"
            elif isinstance(args[0], str):
                 current_ticker = args[0] # If called like process_single_ticker
                 status_prefix = "Analyzing"
        elif func.__name__ == "get_holdings":
            status_prefix = "Fetching holdings"

        try:
            progress.update_status(agent_name, ticker=current_ticker, status=f"{status_prefix}...")
            result = func(*args, **kwargs)
            progress.update_status(agent_name, ticker=current_ticker, status="Done") # Simplified final status
            return result
        except Exception as e:
            logger.error(f"Error in wrapped function {func.__name__} for {agent_name}: {str(e)}")
            progress.update_status(agent_name, ticker=current_ticker, status=f"Error: {str(e)[:50]}...") # Show truncated error
            raise e # Re-raise the exception so the agent knows it failed
    return wrapper

def get_analysts() -> Dict[str, Tuple[str, Callable]]:
    """Get available analysts with their display names and functions"""
    logger.debug("Getting available analysts")
    analysts = {
        'Warren Buffett': ('Warren Buffett', warren_buffett_analyst),
        'Benjamin Graham': ('Benjamin Graham', ben_graham_analyst),
    }
    logger.debug(f"Found {len(analysts)} analysts")
    return analysts

def select_analyst() -> Tuple[str, Callable]:
    """Interactive analyst selection using questionary"""
    logger.info("Starting analyst selection process")
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
        logger.error("No analyst was selected")
        raise ValueError("No analyst selected")

    logger.info(f"Selected analyst: {selected}")
    return analysts[selected]

def main():
    console = Console()
    logger.info("Starting Indian AI Hedge Fund application")

    try:
        # Get analyst selection
        selected_name, selected_analyst = select_analyst()

        console.print(f"\n[bold green]Selected analyst:[/bold green] {selected_name}\n")

        # Convert analyst name to tool name format
        tool_analyst_name = f"{selected_name.lower().replace(' ', '_')}_agent"
        logger.debug(f"Converted analyst name to tool format: {tool_analyst_name}")

        # Create LangChain tools with progress tracking wrappers
        logger.debug("Creating LangChain tools")
        portfolio_agent_name = "portfolio_management"
        tools = [
            StructuredTool(
                name="get_holdings",
                description="Get the user's portfolio holdings from Zerodha",
                func=wrap_with_progress(get_holdings, portfolio_agent_name),
                args_schema=GetHoldingsArgs,
                return_direct=False
            ),
            StructuredTool(
                name=f"{tool_analyst_name}_analyst", # Tool name for the agent
                description=f"Analyzes stocks using {selected_name}'s principles and LLM reasoning. Takes a list of stock tickers as input.",
                func=wrap_with_progress(selected_analyst, tool_analyst_name), # Pass the specific agent name
                args_schema=AnalystArgs,
                return_direct=False
            )
        ]

        logger.debug("Setting up LangChain prompt")

        # Create the LangGraph agent
        logger.info("Creating LangGraph agent")
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=SYSTEM_PROMPT
        )

        # Run the analysis
        console.print("\n[bold blue]Starting Portfolio Analysis...[/bold blue]")
        console.print("[dim]This may take a few minutes[/dim]\n")

        # Start progress tracking
        progress.start()
        progress.update_status(portfolio_agent_name, status="Thinking...") # Initial state for main agent

        response = None # Initialize response
        try:
            logger.info("Running LangGraph agent")
            # Agent execution will trigger the wrapped tools and thus progress updates
            response = agent.invoke({"messages": [("user", HUMAN_PROMPT)]})
            logger.info("LangGraph agent completed successfully")
            progress.update_status(portfolio_agent_name, status="Finished analysis")
        except Exception as e:
            logger.error(f"Error running agent: {str(e)}")
            progress.update_status(portfolio_agent_name, status=f"Error during analysis: {str(e)}")
            console.print(f"\n[red bold]Error during analysis:[/red bold] {str(e)}")
            # traceback.print_exc() # Already printed in finally block
            # No need to raise e here, let finally handle cleanup

        # Display results (only if response is available)
        if response:
            console.print("\n[bold green]✓ Portfolio analysis completed successfully![/bold green]\n")
            console.print("[bold blue]Analysis Results:[/bold blue]")
            console.print("─" * 80)
            # Ensure content exists before printing
            if response.get("messages") and len(response["messages"]) > 0:
                 final_content = response["messages"][-1].content
                 console.print(Markdown(final_content))
            else:
                 console.print("[yellow]No final analysis message found in response.[/yellow]")
            console.print("─" * 80 + "\n")
        else:
            console.print("[red]Analysis could not be completed due to errors.[/red]")

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        # Catch errors during setup (like analyst selection)
        logger.exception("An error occurred during setup or execution")
        console.print(f"\n[red bold]Error:[/red bold] {str(e)}")
        traceback.print_exc()
    finally:
        # Always stop the progress display at the end
        logger.info("Stopping progress tracking")
        progress.stop()
        logger.info("Progress tracking stopped")

if __name__ == "__main__":
    main()
