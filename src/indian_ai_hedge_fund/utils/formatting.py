import pandas as pd
import json
from typing import Any, List, Dict, Union
from indian_ai_hedge_fund.analysts.models import AnalystReport
from indian_ai_hedge_fund.utils.logging_config import logger

def format_holdings_for_prompt(holdings_data: Union[List[Dict[str, Any]], pd.DataFrame, None]) -> str:
    """
    Formats holdings data (list of dicts or DataFrame) into a string for LLM prompts.

    Selects key columns and presents them in a readable format.

    Args:
        holdings_data: The holdings data, either as a list of dictionaries
                       or a pandas DataFrame.

    Returns:
        A formatted string representation of the holdings or a message
        indicating data unavailability.
    """
    if holdings_data is None:
        return "Holdings data not available."

    holdings_df = None
    if isinstance(holdings_data, list):
        if not holdings_data:
            return "Holdings portfolio is empty."
        try:
            holdings_df = pd.DataFrame(holdings_data)
        except Exception as e:
            return f"Could not convert holdings list to DataFrame: {e}"
    elif isinstance(holdings_data, pd.DataFrame):
        if holdings_data.empty:
            return "Holdings portfolio is empty."
        holdings_df = holdings_data
    else:
        # Fallback for unexpected types, return raw string representation
        return f"Current Portfolio Holdings (raw/unprocessed):\n```\n{str(holdings_data)}\n```"

    # Define the columns we want to display
    required_columns = ['tradingsymbol', 'quantity', 'average_price', 'last_price', 'pnl']
    available_columns = [col for col in required_columns if col in holdings_df.columns]

    if not available_columns:
        return f"Holdings data found, but missing key columns ({', '.join(required_columns)}). Raw data:\n```\n{holdings_df.to_string()}\n```"

    # Select and format the DataFrame
    formatted_df = holdings_df[available_columns]

    # Use to_markdown for better LLM readability if available, else to_string
    try:
        holdings_str = formatted_df.to_markdown(index=False)
        header = "Current Portfolio Holdings (Markdown):"
    except ImportError:
        holdings_str = formatted_df.to_string(index=False)
        header = "Current Portfolio Holdings (String):"


    return f"{header}\n```\n{holdings_str}\n```"

def format_analyst_report_for_prompt(analyst_name: str, report: dict[str, AnalystReport]) -> str:
    try:
        # Convert AnalystReport objects to dictionaries
        serializable_report = {k: v.model_dump() for k, v in report.items()}
        return f"""

### {analyst_name} Report
```json
{json.dumps(serializable_report, indent=2)}
```

"""
    except Exception as e:
        logger.error(f"Error formatting analyst report for {analyst_name}: {e}")
        # Fallback to basic string representation if serialization fails
        try:
            return f"### {analyst_name} Report\\n```\\n{str(report)}\\n```"
        except Exception as fallback_e:
            logger.error(f"Error creating fallback string for analyst report {analyst_name}: {fallback_e}")
            # If even string conversion fails, return a minimal error message
            return ""
