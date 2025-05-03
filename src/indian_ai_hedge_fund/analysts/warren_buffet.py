from pydantic import BaseModel
import json
from typing_extensions import Literal
from indian_ai_hedge_fund.tools.finance import get_latest_financial_metrics, FinancialMetrics, get_historical_financial_metrics
from indian_ai_hedge_fund.utils.logging_config import logger
from indian_ai_hedge_fund.llm.models import llm
from indian_ai_hedge_fund.prompts.warrent_buffet import SYSTEM_PROMPT, HUMAN_PROMPT
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import ChatPromptTemplate
from indian_ai_hedge_fund.utils.progress import progress
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from tenacity import RetryCallState
from indian_ai_hedge_fund.analysts.models import AnalystReport

def process_single_ticker(ticker: str) -> tuple[str, dict[str, any]]:
    """
    Process a single ticker for Warren Buffett analysis.

    Args:
        ticker: Stock ticker to analyze

    Returns:
        Tuple of (ticker, analysis_result)
    """
    try:
        logger.info(f"Analyzing {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Analyzing")

        logger.info(f"Fetching financial metrics for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Fetching metrics")
        metrics = get_latest_financial_metrics(ticker)
        historical_metrics = get_historical_financial_metrics(ticker, periods=5)
        logger.info(f"Finished fetching financial metrics for {ticker}")

        logger.debug(f"Latest metrics: {metrics}")
        logger.debug(f"Historical metrics: {historical_metrics}")

        logger.info(f"Getting market cap for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Calculating market cap")
        market_cap = metrics.market_cap

        logger.info(f"Analyzing fundamentals for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Analyzing fundamentals")
        fundamental_analysis = analyze_fundamentals(metrics)
        logger.info(f"Finished analyzing fundamentals for {ticker}")

        logger.debug(f"Fundamental analysis: {fundamental_analysis}")

        logger.info(f"Analyzing consistency for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Analyzing consistency")
        consistency_analysis = analyze_consistency(historical_metrics)
        logger.info(f"Finished analyzing consistency for {ticker}")

        logger.debug(f"Consistency analysis: {consistency_analysis}")

        logger.info(f"Analyzing moat for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Analyzing moat")
        moat_analysis = analyze_moat(historical_metrics)
        logger.info(f"Finished analyzing moat for {ticker}")

        logger.debug(f"Moat Analysis: {moat_analysis}")

        logger.info(f"Analyzing management quality for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Analyzing management")
        mgmt_analysis = analyze_management_quality(metrics)
        logger.info(f"Finished analyzing management quality for {ticker}")

        logger.debug(f"Management Quality: {mgmt_analysis}")

        logger.info(f"Calculating intrinsic value for {ticker}")
        progress.update_status("warren_buffett_agent", ticker, "Calculating intrinsic value")
        intrinsic_value_analysis = calculate_intrinsic_value(metrics)
        logger.info(f"Finished calculating intrinsic value for {ticker}")

        logger.debug(f"Intrinsic Value: {intrinsic_value_analysis}")

        # Calculate total score
        total_score = fundamental_analysis["score"] + consistency_analysis["score"] + moat_analysis["score"] + mgmt_analysis["score"]

        max_possible_score = 10 + moat_analysis["max_score"] + mgmt_analysis["max_score"]

        # Add margin of safety analysis if we have both intrinsic value and current price
        margin_of_safety = None
        intrinsic_value = intrinsic_value_analysis["intrinsic_value"]
        if intrinsic_value and market_cap:
            margin_of_safety = (intrinsic_value - market_cap) / market_cap

        # Generate trading signal
        if (total_score >= 0.7 * max_possible_score) and margin_of_safety and (margin_of_safety >= 0.3):
            signal = "bullish"
        elif total_score <= 0.3 * max_possible_score or (margin_of_safety is not None and margin_of_safety < -0.3):
            signal = "bearish"
        else:
            signal = "neutral"

        # Combine all analysis results
        analysis_data = {
            "signal": signal,
            "score": total_score,
            "max_score": max_possible_score,
            "fundamental_analysis": fundamental_analysis,
            "consistency_analysis": consistency_analysis,
            "moat_analysis": moat_analysis,
            "management_analysis": mgmt_analysis,
            "intrinsic_value_analysis": intrinsic_value_analysis,
            "market_cap": market_cap,
            "margin_of_safety": margin_of_safety,
        }

        logger.info(f"Analysis Data for {ticker}: {analysis_data}")

        progress.update_status("warren_buffett_agent", ticker, "Generating final signal")
        buffett_signal = generate_buffett_output(ticker, analysis_data)
        logger.info(f"Buffett analysis for {ticker}: {buffett_signal}")

        progress.update_status("warren_buffett_agent", ticker, "Done")
        return ticker, buffett_signal

    except Exception as e:
        logger.exception(f"Error analyzing {ticker}: {str(e)}")
        progress.update_status("warren_buffett_agent", ticker, "Error")
        return ticker, None

def warren_buffett_analyst(tickers: list[str]) -> dict[str, any]:
    """
    Analyzes stocks using Buffett's principles and LLM reasoning in parallel.

    Args:
        tickers: List of stock tickers to analyze

    Returns:
        Dictionary with ticker as key and analysis data as value
    """
    buffett_analysis = {}

    try:
        # Use ThreadPoolExecutor for parallel processing
        # Number of workers is min(32, len(tickers)) to avoid creating too many threads
        with ThreadPoolExecutor(max_workers=min(2, len(tickers))) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(process_single_ticker, ticker): ticker
                for ticker in tickers
            }

            # Process completed tasks as they finish
            # Progress updates for individual tickers happen inside process_single_ticker
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    ticker, result = future.result()
                    if result is not None:
                        buffett_analysis[ticker] = result
                except Exception as e:
                    logger.exception(f"Error processing {ticker}: {str(e)}")
                    # The error status is set within process_single_ticker
                    # try:
                    #     progress.update_status("warren_buffett_agent", ticker, "Error")
                    # except Exception as pe:
                    #     logger.error(f"Error updating progress for {ticker}: {str(pe)}")
                    continue
    except Exception as e:
        logger.exception(f"Error in Warren Buffett analyst thread pool: {str(e)}")
    # finally:
        # Update final status - REMOVED (handled by wrapper in main.py)
        # try:
        #     logger.info("Updating final status in Warren Buffett analyst")
        #     progress.update_status("warren_buffett_agent", status="Analysis complete")
        # except Exception as e:
        #     logger.error(f"Error updating final progress status: {str(e)}")

    return buffett_analysis

    # # Create the message
    # message = HumanMessage(content=json.dumps(buffett_analysis), name="warren_buffett_agent")

    # # Show reasoning if requested
    # if state["metadata"]["show_reasoning"]:
    #     show_agent_reasoning(buffett_analysis, "Warren Buffett Agent")

    # # Add the signal to the analyst_signals list
    # state["data"]["analyst_signals"]["warren_buffett_agent"] = buffett_analysis

    # return {"messages": [message], "data": state["data"]}

def analyze_fundamentals(metrics: FinancialMetrics) -> dict[str, any]:
    """Analyze company fundamentals based on Buffett's criteria."""

    score = 0
    reasoning = []

    # Check ROE (Return on Equity)
    if metrics.return_on_equity and metrics.return_on_equity > 0.15:  # 15% ROE threshold
        score += 2
        reasoning.append(f"Strong ROE of {metrics.return_on_equity:.1%}")
    elif metrics.return_on_equity:
        reasoning.append(f"Weak ROE of {metrics.return_on_equity:.1%}")
    else:
        reasoning.append("ROE data not available")

    # Check Debt to Equity
    if metrics.debt_to_equity_ratio and metrics.debt_to_equity_ratio < 0.5:
        score += 2
        reasoning.append("Conservative debt levels")
    elif metrics.debt_to_equity_ratio:
        reasoning.append(f"High debt to equity ratio of {metrics.debt_to_equity_ratio:.1f}")
    else:
        reasoning.append("Debt to equity data not available")

    # Check Operating Margin
    if metrics.operating_margin and metrics.operating_margin > 0.15:
        score += 2
        reasoning.append("Strong operating margins")
    elif metrics.operating_margin:
        reasoning.append(f"Weak operating margin of {metrics.operating_margin:.1%}")
    else:
        reasoning.append("Operating margin data not available")

    # Check Current Ratio
    if metrics.current_ratio and metrics.current_ratio > 1.5:
        score += 1
        reasoning.append("Good liquidity position")
    elif metrics.current_ratio:
        reasoning.append(f"Weak liquidity with current ratio of {metrics.current_ratio:.1f}")
    else:
        reasoning.append("Current ratio data not available")

    return {"score": score, "details": "; ".join(reasoning), "metrics": metrics.model_dump()}

def analyze_consistency(historical_metrics: list[FinancialMetrics]) -> dict[str, any]:
    """Analyze earnings consistency and growth."""
    if len(historical_metrics) < 4:  # Need at least 4 periods for trend analysis
        return {"score": 0, "details": "Insufficient historical data"}

    score = 0
    reasoning = []

    # Check earnings growth trend
    earnings_values = [item.net_income for item in historical_metrics if item.net_income]
    if len(earnings_values) >= 4:
        # Simple check: is each period's earnings bigger than the next?
        earnings_growth = all(earnings_values[i] > earnings_values[i + 1] for i in range(len(earnings_values) - 1))

        if earnings_growth:
            score += 3
            reasoning.append("Consistent earnings growth over past periods")
        else:
            reasoning.append("Inconsistent earnings growth pattern")

        # Calculate total growth rate from oldest to latest
        if len(earnings_values) >= 2 and earnings_values[-1] != 0:
            growth_rate = (earnings_values[0] - earnings_values[-1]) / abs(earnings_values[-1])
            reasoning.append(f"Total earnings growth of {growth_rate:.1%} over past {len(earnings_values)} periods")
    else:
        reasoning.append("Insufficient earnings data for trend analysis")

    return {
        "score": score,
        "details": "; ".join(reasoning),
    }

def analyze_moat(historical_metrics: list[FinancialMetrics]) -> dict[str, any]:
    """
    Evaluate whether the company likely has a durable competitive advantage (moat).
    For simplicity, we look at stability of ROE/operating margins over multiple periods
    or high margin over the last few years. Higher stability => higher moat score.
    """
    if not historical_metrics or len(historical_metrics) < 3:
        return {"score": 0, "max_score": 3, "details": "Insufficient data for moat analysis"}

    reasoning = []
    moat_score = 0
    historical_roes = []
    historical_margins = []

    for m in historical_metrics:
        if m.return_on_equity is not None:
            historical_roes.append(m.return_on_equity)
        if m.operating_margin is not None:
            historical_margins.append(m.operating_margin)


    logger.debug("Historical ROEs: %s", historical_roes)
    logger.debug("Historical Margins: %s", historical_margins)

    # Check for stable or improving ROE
    if len(historical_roes) >= 3:
        stable_roe = all(r > 0.15 for r in historical_roes)
        if stable_roe:
            moat_score += 1
            reasoning.append("Stable ROE above 15% across periods (suggests moat)")
        else:
            reasoning.append("ROE not consistently above 15%")

    # Check for stable or improving operating margin
    if len(historical_margins) >= 3:
        stable_margin = all(m > 0.15 for m in historical_margins)
        if stable_margin:
            moat_score += 1
            reasoning.append("Stable operating margins above 15% (moat indicator)")
        else:
            reasoning.append("Operating margin not consistently above 15%")

    # If both are stable/improving, add an extra point
    if moat_score == 2:
        moat_score += 1
        reasoning.append("Both ROE and margin stability indicate a solid moat")

    return {
        "score": moat_score,
        "max_score": 3,
        "details": "; ".join(reasoning),
    }

def analyze_management_quality(metrics: FinancialMetrics) -> dict[str, any]:
    """
    Checks for share dilution or consistent buybacks, and some dividend track record.
    A simplified approach:
      - if there's net share repurchase or stable share count, it suggests management
        might be shareholder-friendly.
      - if there's a big new issuance, it might be a negative sign (dilution).
    """

    reasoning = []
    mgmt_score = 0

    latest = metrics
    if hasattr(latest, "issuance_or_purchase_of_equity_shares") and latest.issuance_or_purchase_of_equity_shares and latest.issuance_or_purchase_of_equity_shares < 0:
        # Negative means the company spent money on buybacks
        mgmt_score += 1
        reasoning.append("Company has been repurchasing shares (shareholder-friendly)")

    if hasattr(latest, "issuance_or_purchase_of_equity_shares") and latest.issuance_or_purchase_of_equity_shares and latest.issuance_or_purchase_of_equity_shares > 0:
        # Positive issuance means new shares => possible dilution
        reasoning.append("Recent common stock issuance (potential dilution)")
    else:
        reasoning.append("No significant new stock issuance detected")

    # Check for any dividends
    if hasattr(latest, "dividends_and_other_cash_distributions") and latest.dividends_and_other_cash_distributions and latest.dividends_and_other_cash_distributions < 0:
        mgmt_score += 1
        reasoning.append("Company has a track record of paying dividends")
    else:
        reasoning.append("No or minimal dividends paid")

    return {
        "score": mgmt_score,
        "max_score": 2,
        "details": "; ".join(reasoning),
    }

def calculate_owner_earnings(metrics: FinancialMetrics) -> dict[str, any]:
    """Calculate owner earnings (Buffett's preferred measure of true earnings power).
    Owner Earnings = Net Income + Depreciation - Maintenance CapEx"""


    latest = metrics

    net_income = latest.net_income
    depreciation = latest.depreciation_and_amortization
    capex = latest.capital_expenditure

    if not all([net_income, depreciation, capex]):
        return {"owner_earnings": None, "details": ["Missing components for owner earnings calculation"]}

    # Estimate maintenance capex (typically 70-80% of total capex)
    maintenance_capex = capex * 0.75
    owner_earnings = net_income + depreciation - maintenance_capex

    return {
        "owner_earnings": owner_earnings,
        "components": {"net_income": net_income, "depreciation": depreciation, "maintenance_capex": maintenance_capex},
        "details": ["Owner earnings calculated successfully"],
    }

def calculate_intrinsic_value(metrics: FinancialMetrics) -> dict[str, any]:
    """Calculate intrinsic value using DCF with owner earnings."""


    # Calculate owner earnings
    earnings_data = calculate_owner_earnings(metrics)
    if not earnings_data["owner_earnings"]:
        return {"intrinsic_value": None, "details": earnings_data["details"]}

    owner_earnings = earnings_data["owner_earnings"]

    # Get current market data
    latest_financial_line_items = metrics
    shares_outstanding = latest_financial_line_items.outstanding_shares

    if not shares_outstanding:
        return {"intrinsic_value": None, "details": ["Missing shares outstanding data"]}

    # Buffett's DCF assumptions (conservative approach)
    growth_rate = 0.05  # Conservative 5% growth
    discount_rate = 0.09  # Typical ~9% discount rate
    terminal_multiple = 12
    projection_years = 10

    # Sum of discounted future owner earnings
    future_value = 0
    for year in range(1, projection_years + 1):
        future_earnings = owner_earnings * (1 + growth_rate) ** year
        present_value = future_earnings / (1 + discount_rate) ** year
        future_value += present_value

    # Terminal value
    terminal_value = (owner_earnings * (1 + growth_rate) ** projection_years * terminal_multiple) / ((1 + discount_rate) ** projection_years)

    intrinsic_value = future_value + terminal_value

    return {
        "intrinsic_value": intrinsic_value,
        "owner_earnings": owner_earnings,
        "assumptions": {
            "growth_rate": growth_rate,
            "discount_rate": discount_rate,
            "terminal_multiple": terminal_multiple,
            "projection_years": projection_years,
        },
        "details": ["Intrinsic value calculated using DCF model with owner earnings"],
    }

# Define the callback function for logging and status updates during retries
def log_and_update_status_before_retry(retry_state: RetryCallState):
    """Log retry attempts and update progress status."""
    ticker = retry_state.args[0] if retry_state.args else "unknown ticker"
    attempt_num = retry_state.attempt_number
    logger.warning(f"LLM call for {ticker} failed (attempt {attempt_num}), retrying...")
    progress.update_status("warren_buffett_agent", ticker, f"Retrying LLM ({attempt_num})")

# Apply retry decorator for LLM calls
# Retry up to 5 times with exponential backoff (1s, 2s, 4s, 8s, 16s) max 10s wait.
# Consider refining retry_on_exception to specific API errors (e.g., RateLimitError, APIError)
# if the LLM library provides them.
@retry(
    stop=stop_after_attempt(5), # Increased retries to 5
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=log_and_update_status_before_retry, # Add callback before sleep
    # retry=retry_if_exception_type(Exception) # Default retries on any Exception
)
def generate_buffett_output(
    ticker: str,
    analysis_data: dict[str, any]
) -> AnalystReport:
    """Get investment decision from LLM with Buffett's principles"""
    logger.info(f"Generating Buffett output for {ticker}") # Add logging
    try:
        template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    SYSTEM_PROMPT,
                ),
                (
                    "human",
                    HUMAN_PROMPT,
                ),
            ]
        )

        prompt = template.invoke({"analysis_data": json.dumps(analysis_data, indent=2), "ticker": ticker})

        response = llm.with_structured_output(AnalystReport).invoke(prompt)
        logger.info(f"Successfully generated Buffett output for {ticker}") # Add logging
        return response
    except RetryError as e:
        # Log the final error after retries are exhausted
        logger.error(f"LLM call failed for {ticker} after multiple retries: {e}")
        # Reraise the last exception captured by tenacity
        raise e.last_attempt.exception()
    except Exception as e:
        # Log and re-raise other unexpected errors during the call
        logger.error(f"Unexpected error during LLM call for {ticker}: {e}")
        raise e

