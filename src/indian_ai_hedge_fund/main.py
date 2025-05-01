from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import StructuredTool
from langgraph.prebuilt import create_react_agent
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
from indian_ai_hedge_fund.analysts.config import get_analysts

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

def select_analyst() -> List[Tuple[str, Callable]]:
    """Interactive analyst selection using questionary"""
    logger.info("Starting analyst selection process")
    analysts = get_analysts()

    # Create choices list
    choices = [
        questionary.Choice(
            title=name,
            value=name # Use name as the value to retrieve from the dict later
        )
        for name in analysts.keys()
    ]

    # Show checkbox prompt for multiple selections
    selected_names = questionary.checkbox( # Changed from select to checkbox
        "Select your AI analysts (use spacebar to select, enter to confirm)",
        choices=choices,
        # use_indicator=True, # Checkbox doesn't use indicator in the same way
        style=questionary.Style([
            ('qmark', 'fg:yellow bold'),
            ('question', 'bold'),
            ('answer', 'fg:green bold'),
            # ('pointer', 'fg:yellow bold'), # Different style for checkbox
            ('highlighted', 'fg:yellow bold'),
            ('selected', 'fg:cyan bold') # Style for selected items
        ])
    ).ask()

    if not selected_names: # Check if the list is empty
        logger.error("No analyst was selected")
        raise ValueError("No analyst selected")

    # Retrieve the (name, function) tuples for selected analysts
    selected_analysts = [analysts[name] for name in selected_names]

    logger.info(f"Selected analysts: {[name for name, _ in selected_analysts]}")
    return selected_analysts # Return the list of selected analyst tuples

def main():
    console = Console()
    logger.info("Starting Indian AI Hedge Fund application")

    try:
        # Get analyst selection (now returns a list)
        selected_analysts = select_analyst() # Returns List[Tuple[str, Callable]]

        selected_names_str = ", ".join([name for name, _ in selected_analysts])
        console.print(f"\n[bold green]Selected analysts:[/bold green] {selected_names_str}\n")

        # Create LangChain tools with progress tracking wrappers
        logger.debug("Creating LangChain tools")
        portfolio_agent_name = "portfolio_management"
        # Start with the holdings tool
        tools = [
            StructuredTool(
                name="get_holdings",
                description="Get the user's portfolio holdings from Zerodha",
                func=wrap_with_progress(get_holdings, portfolio_agent_name),
                args_schema=GetHoldingsArgs,
                return_direct=False
            )
        ]

        # Add a tool for each selected analyst
        for name, analyst_func in selected_analysts:
            tool_analyst_name = f"{name.lower().replace(' ', '_')}_analyst"
            logger.debug(f"Creating tool for analyst: {name} ({tool_analyst_name})")
            tools.append(
                StructuredTool(
                    name=tool_analyst_name,
                    description=f"Analyzes stocks using {name}'s principles and LLM reasoning. Takes a list of stock tickers as input.",
                    func=wrap_with_progress(analyst_func, tool_analyst_name), # Pass specific tool name
                    args_schema=AnalystArgs,
                    return_direct=False
                )
            )

        logger.debug(f"Total tools created: {len(tools)}")
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
