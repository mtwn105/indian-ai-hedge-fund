from langchain_core.prompts import ChatPromptTemplate
from rich.markdown import Markdown
from rich.console import Console
from rich.table import Table as RichTable
import questionary
from indian_ai_hedge_fund.tools.zerodha import get_holdings
from typing import List, Dict, Tuple, Callable, Any
from indian_ai_hedge_fund.llm.models import llm
from indian_ai_hedge_fund.utils.logging_config import logger
from indian_ai_hedge_fund.utils.progress import progress
import traceback
from functools import wraps
from indian_ai_hedge_fund.analysts.config import get_analysts
import pandas as pd
import json
from indian_ai_hedge_fund.prompts.portfolio_review import SYSTEM_PROMPT, HUMAN_SYNTHESIS_TEMPLATE
from indian_ai_hedge_fund.utils.formatting import format_holdings_for_prompt, format_analyst_report_for_prompt
from datetime import datetime
from indian_ai_hedge_fund.utils.pdf_generator import generate_pdf_report

def wrap_with_progress(func: Callable, agent_name: str, task_description: str = "Executing task") -> Callable:
    """Wrap a function with progress tracking updates using AgentProgress."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Attempt to determine ticker for status update if possible (basic version)
        current_ticker = None
        status_prefix = task_description
        if "analyst" in agent_name.lower() and 'tickers' in kwargs and isinstance(kwargs['tickers'], list) and len(kwargs['tickers']) == 1:
             current_ticker = kwargs['tickers'][0]
             status_prefix = f"Analyzing {current_ticker}"
        elif "analyst" in agent_name.lower() and args and isinstance(args[0], list) and len(args[0]) == 1:
             current_ticker = args[0][0]
             status_prefix = f"Analyzing {current_ticker}"
        elif func.__name__ == "get_holdings":
             status_prefix = "Fetching holdings"

        try:
            progress.update_status(agent_name, ticker=current_ticker, status=f"{status_prefix}...")
            result = func(*args, **kwargs)
            progress.update_status(agent_name, ticker=current_ticker, status="Done") # Simplified final status
            return result
        except Exception as e:
            error_msg = f"Error in {func.__name__} for {agent_name}: {str(e)}"
            logger.error(error_msg)
            progress.update_status(agent_name, ticker=current_ticker, status=f"Error: {str(e)[:50]}...") # Show truncated error
            raise e # Re-raise the exception
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
        # 1. Get analyst selection
        selected_analysts = select_analyst()
        selected_names_str = ", ".join([name for name, _ in selected_analysts])
        console.print(f"\n[bold green]Selected analysts:[/bold green] {selected_names_str}\n")

        # Start progress tracking using AgentProgress
        progress.start()

        # 2. Fetch holdings
        holdings_data = None
        holdings_df = None
        try:
            logger.info("Fetching portfolio holdings...")
            # Wrap and call with agent name
            holdings_func_wrapped = wrap_with_progress(
                get_holdings,
                "Holdings Fetcher", # Agent name
                "Fetching portfolio"
            )
            holdings_data = holdings_func_wrapped()
            logger.info("Successfully fetched holdings.")
            # Attempt to convert holdings to DataFrame for easier processing
            if isinstance(holdings_data, list) and holdings_data:
                 holdings_df = pd.DataFrame(holdings_data)
                 logger.debug("Converted holdings to DataFrame.")
                 # Log first few rows for debugging
                 logger.debug(f"Holdings DataFrame head:\n{holdings_df.head().to_string()}")
            elif isinstance(holdings_data, pd.DataFrame):
                 holdings_df = holdings_data # Already a DataFrame
                 logger.debug(f"Holdings received as DataFrame head:\n{holdings_df.head().to_string()}")
            else:
                 logger.warning(f"Holdings data is not a list or DataFrame: {type(holdings_data)}")

        except Exception as e:
            logger.error(f"Failed to fetch or process holdings: {e}")
            console.print(f"\n[red bold]Error fetching holdings:[/red bold] {str(e)}")
            # Optionally re-raise or handle differently depending on whether analysis can proceed
            raise # Re-raise to stop execution if holdings are essential

        # 3. Extract Tickers (ensure holdings_df exists and has the column)
        tickers = []
        if holdings_df is not None and 'tradingsymbol' in holdings_df.columns:
            tickers = holdings_df['tradingsymbol'].unique().tolist()
            logger.info(f"Extracted {len(tickers)} unique tickers for analysis: {tickers}")
        elif holdings_df is not None:
             logger.warning("Could not find 'tradingsymbol' column in holdings DataFrame.")
             console.print("[yellow]Warning: Could not extract tickers from holdings data.[/yellow]")
             # Decide if you want to proceed without tickers or ask the user
             # For now, we'll proceed but analysts might fail if they require tickers
        else:
             logger.warning("Holdings data is not available or not in expected format to extract tickers.")
             console.print("[yellow]Warning: Holdings data unavailable or malformed. Cannot extract tickers.[/yellow]")
             # Proceeding without tickers, analysts might fail

        if not tickers:
            console.print("[yellow]Warning: No tickers found to analyze. Skipping analyst reports.[/yellow]")
            analyst_reports = {} # Ensure analyst_reports exists even if empty
        else:
            # 4. Run selected analysts
            analyst_reports = {}
            console.print(f"\n[bold blue]Running {len(selected_analysts)} selected analyst(s) on {len(tickers)} ticker(s)...[/bold blue]")
            for name, analyst_func in selected_analysts:
                logger.info(f"Running analyst: {name}")
                try:
                    # Wrap and call analyst function with agent name
                    analyst_func_wrapped = wrap_with_progress(
                        analyst_func,
                        name, # Use analyst name as agent name
                        f"Running {name}"
                    )
                    report = analyst_func_wrapped(tickers=tickers)
                    analyst_reports[name] = report
                    logger.info(f"Analyst {name} completed.")
                except Exception as e:
                    error_msg = f"Error running analyst {name}: {e}"
                    logger.error(error_msg)
                    console.print(f"[red bold]Error running analyst {name}:[/red bold] {str(e)}")
                    analyst_reports[name] = f"Error: Failed to generate report - {e}" # Store error message

        # Display individual analyst reports before synthesis
        if analyst_reports:
            console.print("\n" + "─" * 80)
            console.print("[bold cyan]Individual Analyst Reports:[/bold cyan]")
            for name, report in analyst_reports.items():
                console.print(f"\n[bold yellow]Report from {name}:[/bold yellow]")
                # Check if the report is a dictionary (like from Technical Analyst)
                if isinstance(report, dict):
                    # Create a table for dictionary reports using RichTable
                    table = RichTable(header_style="bold magenta", show_lines=True)
                    table.add_column("Ticker", style="dim", width=12)
                    table.add_column("Signal")
                    table.add_column("Confidence (%)", justify="right")
                    table.add_column("Reasoning")

                    # Define signal colors
                    signal_colors = {
                        "bullish": "green",
                        "bearish": "red",
                        "neutral": "yellow"
                    }

                    for ticker, analysis in report.items():
                        # Assuming analysis is an object with .signal, .confidence, and .reasoning attributes
                        signal = getattr(analysis, 'signal', 'N/A')
                        confidence = getattr(analysis, 'confidence', 'N/A')
                        reasoning = getattr(analysis, 'reasoning', 'N/A')

                        # Get color for signal, default to white if signal not in map
                        signal_color = signal_colors.get(str(signal).lower(), "white")

                        table.add_row(
                            f"[bold]{ticker}[/bold]", # Make ticker bold
                            f"[{signal_color}]{str(signal)}[/{signal_color}]", # Color signal
                            f"{confidence:.1f}" if isinstance(confidence, (float, int)) else str(confidence),
                            str(reasoning)
                        )
                    console.print(table)
                elif isinstance(report, str):
                     # Use Markdown for potentially formatted string reports, handles plain text too
                     console.print(Markdown(report))
                else:
                     # Handle other non-string/non-dict reports if necessary
                     # For now, just convert to string for display
                     console.print(str(report))
            console.print("─" * 80 + "\n")
        else:
            console.print("\n[yellow]No individual analyst reports to display.[/yellow]\n")

        # 5. Prepare data for LLM
        logger.info("Preparing final prompt for LLM synthesis")

        # Format holdings using the utility function and add heading
        formatted_holdings = format_holdings_for_prompt(holdings_df if holdings_df is not None else holdings_data)
        holdings_str = f"## Holdings\n\n{formatted_holdings}"
        logger.debug(f"Formatted holdings string for prompt:\n{holdings_str}")

        # Format analyst reports with headings and subheadings
        reports_str = "## Analyst Reports\n\n"

        if analyst_reports:
            for name, report in analyst_reports.items():
                 reports_str += format_analyst_report_for_prompt(name, report)

        else:
            reports_str += "No analyst reports were generated (possibly due to missing tickers, errors, or no analysts selected)."

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),         # Use combined system prompt
            ("human", HUMAN_SYNTHESIS_TEMPLATE)    # Use imported template string
        ])

        chain = prompt | llm

        console.print("\n[bold blue]Synthesizing Analysis...[/bold blue]")
        logger.info("Invoking LLM for final synthesis")
        # Use progress.update_status for synthesis step
        progress.update_status("Synthesizer", status="Generating final report...")

        final_response = None
        try:
            # Invoke the chain, passing the actual data for the placeholders
            invoke_input = {
                "holdings_data": holdings_str,
                "analyst_reports": reports_str
            }
            response_obj = chain.invoke(invoke_input)
            final_response = response_obj.content # Extract content from AIMessage or similar
            logger.info("LLM synthesis completed successfully.")
            progress.update_status("Synthesizer", status="Done") # Mark as complete
        except Exception as e:
            logger.error(f"Error during LLM synthesis: {e}")
            progress.update_status("Synthesizer", status=f"Error: {str(e)[:50]}...")
            console.print(f"\n[red bold]Error during final synthesis:[/red bold] {str(e)}")
            # final_response remains None

        # 7. Display results
        if final_response:
            console.print("\n[bold green]✓ Portfolio analysis synthesized successfully![/bold green]\n")
            console.print("[bold blue]Synthesized Analysis Results:[/bold blue]")
            console.print("─" * 80)
            console.print(Markdown(final_response))
            console.print("─" * 80 + "\n")
        else:
            console.print("[red]Final synthesis could not be completed due to errors.[/red]")

        # 8. Generate PDF report
        # Use holdings_df if available, otherwise fall back to original holdings_data
        holdings_for_pdf = holdings_df if holdings_df is not None else holdings_data
        report_date_str = datetime.now().strftime("%Y%m%d")
        pdf_filename = f"india_ai_hedge_fund_analysis_report_{report_date_str}.pdf"
        try:
            generate_pdf_report(holdings_for_pdf, analyst_reports, final_response, pdf_filename)
            console.print(f"\n[bold green]✓ Analysis report saved to {pdf_filename}[/bold green]")
        except Exception as e:
            logger.error(f"Failed to generate PDF report: {e}")
            console.print(f"\n[red bold]Error generating PDF report:[/red bold] {str(e)}")

    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        # Catch errors during setup (like analyst selection or initial holdings fetch)
        logger.exception("An error occurred during setup or execution")
        console.print(f"\n[red bold]Error:[/red bold] {str(e)}")
        traceback.print_exc()
    finally:
        # Add finally block to ensure progress stops
        logger.info("Stopping progress tracking")
        progress.stop()
        logger.info("Progress tracking stopped")

if __name__ == "__main__":
    main()
