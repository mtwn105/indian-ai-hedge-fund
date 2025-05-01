from pydantic import BaseModel
import json
from typing_extensions import Literal
from indian_ai_hedge_fund.tools.finance import get_latest_financial_metrics, FinancialMetrics, get_historical_financial_metrics
from indian_ai_hedge_fund.utils.logging_config import logger
from indian_ai_hedge_fund.llm.models import llm
from indian_ai_hedge_fund.prompts.ben_graham import SYSTEM_PROMPT, HUMAN_PROMPT
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_core.prompts import ChatPromptTemplate
import math
from indian_ai_hedge_fund.utils.progress import progress
import traceback

class BenGrahamSignal(BaseModel):
    signal: Literal["bullish", "bearish", "neutral"]
    confidence: float
    reasoning: str

def process_single_ticker(ticker: str) -> tuple[str, dict[str, any]]:
    """
    Process a single ticker for Benjamin Graham analysis.

    Args:
        ticker: Stock ticker to analyze

    Returns:
        Tuple of (ticker, analysis_result)
    """
    try:
        logger.info(f"Analyzing {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Analyzing")

        # Fetch financial metrics
        logger.info(f"Fetching financial metrics for {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Fetching metrics")
        metrics = get_latest_financial_metrics(ticker)
        historical_metrics = get_historical_financial_metrics(ticker, periods=10)
        logger.info(f"Finished fetching financial metrics for {ticker}")

        # Get market cap
        logger.info(f"Getting market cap for {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Calculating market cap")
        market_cap = metrics.market_cap

        # Perform sub-analyses
        logger.info(f"Analyzing earnings stability for {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Analyzing earnings")
        earnings_analysis = analyze_earnings_stability(metrics, historical_metrics)
        logger.info(f"Finished analyzing earnings stability for {ticker}")

        logger.info(f"Analyzing financial strength for {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Analyzing financials")
        strength_analysis = analyze_financial_strength(metrics, historical_metrics)
        logger.info(f"Finished analyzing financial strength for {ticker}")

        logger.info(f"Analyzing Graham valuation for {ticker}")
        progress.update_status("ben_graham_agent", ticker, "Calculating valuation")
        valuation_analysis = analyze_valuation_graham(metrics, historical_metrics, market_cap)
        logger.info(f"Finished analyzing Graham valuation for {ticker}")

        # Calculate total score
        total_score = earnings_analysis["score"] + strength_analysis["score"] + valuation_analysis["score"]
        max_possible_score = 15  # total possible from the three analysis functions

        # Generate trading signal based on Graham's principles
        if total_score >= 0.7 * max_possible_score:
            signal = "bullish"
        elif total_score <= 0.3 * max_possible_score:
            signal = "bearish"
        else:
            signal = "neutral"

        # Combine all analysis results
        analysis_data = {
            "signal": signal,
            "score": total_score,
            "max_score": max_possible_score,
            "earnings_analysis": earnings_analysis,
            "strength_analysis": strength_analysis,
            "valuation_analysis": valuation_analysis
        }

        progress.update_status("ben_graham_agent", ticker, "Generating final signal")
        graham_signal = generate_graham_output(ticker, {"ticker": analysis_data})
        progress.update_status("ben_graham_agent", ticker, "Done")
        return ticker, graham_signal

    except Exception as e:
        logger.exception(f"Error analyzing {ticker}: {str(e)}")
        progress.update_status("ben_graham_agent", ticker, "Error")
        return ticker, None

def ben_graham_analyst(tickers: list[str]) -> dict[str, any]:
    """
    Analyzes stocks using Benjamin Graham's classic value-investing principles:
    1. Earnings stability over multiple years.
    2. Solid financial strength (low debt, adequate liquidity).
    3. Discount to intrinsic value (e.g. Graham Number or net-net).
    4. Adequate margin of safety.
    """
    graham_analysis = {}

    # Track if we started the progress display (to avoid stopping if we didn't start)
    # progress_started = False # No longer needed here

    # Start progress tracking - REMOVED (handled by main.py via wrapper)
    # try:
    #     logger.info("Starting progress tracking in Ben Graham analyst")
    #     progress.start()
    #     progress.update_status("ben_graham_agent", status="Starting analysis")
    #     progress_started = True
    #     logger.info("Progress tracking started successfully")
    # except Exception as e:
    #     logger.error(f"Error starting progress tracking: {str(e)}")
    #     traceback.print_exc()

    try:
        # Use ThreadPoolExecutor for parallel processing
        # Number of workers is min(32, len(tickers)) to avoid creating too many threads
        with ThreadPoolExecutor(max_workers=min(32, len(tickers))) as executor:
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
                        graham_analysis[ticker] = result
                except Exception as e:
                    logger.exception(f"Error processing {ticker}: {str(e)}")
                    # The error status is set within process_single_ticker
                    # try:
                    #     progress.update_status("ben_graham_agent", ticker, "Error")
                    # except Exception as pe:
                    #     logger.error(f"Error updating progress for {ticker}: {str(pe)}")
                    continue
    except Exception as e:
        logger.exception(f"Error in Ben Graham analyst thread pool: {str(e)}")
    # finally:
        # Update final status - REMOVED (handled by wrapper in main.py)
        # try:
        #     logger.info("Updating final status in Ben Graham analyst")
        #     progress.update_status("ben_graham_agent", status="Analysis complete")
        # except Exception as e:
        #     logger.error(f"Error updating final progress status: {str(e)}")

    return graham_analysis

def analyze_earnings_stability(metrics: FinancialMetrics, historical_metrics: list[FinancialMetrics]) -> dict:
    """
    Graham wants at least several years of consistently positive earnings (ideally 5+).
    We'll check:
    1. Number of years with positive EPS.
    2. Growth in EPS from first to last period.
    """
    score = 0
    details = []

    if not historical_metrics:
        return {"score": score, "details": "Insufficient data for earnings stability analysis"}

    eps_vals = []
    for item in historical_metrics:
        if item.earnings_per_share is not None:
            eps_vals.append(item.earnings_per_share)

    if len(eps_vals) < 2:
        details.append("Not enough multi-year EPS data.")
        return {"score": score, "details": "; ".join(details)}

    # 1. Consistently positive EPS
    positive_eps_years = sum(1 for e in eps_vals if e > 0)
    total_eps_years = len(eps_vals)
    if positive_eps_years == total_eps_years:
        score += 3
        details.append("EPS was positive in all available periods.")
    elif positive_eps_years >= (total_eps_years * 0.8):
        score += 2
        details.append("EPS was positive in most periods.")
    else:
        details.append("EPS was negative in multiple periods.")

    # 2. EPS growth from earliest to latest
    if eps_vals[-1] > eps_vals[0]:
        score += 1
        details.append("EPS grew from earliest to latest period.")
    else:
        details.append("EPS did not grow from earliest to latest period.")

    return {"score": score, "details": "; ".join(details)}

def analyze_financial_strength(metrics: FinancialMetrics, historical_metrics: list[FinancialMetrics]) -> dict:
    """
    Graham checks liquidity (current ratio >= 2), manageable debt,
    and dividend record (preferably some history of dividends).
    """
    score = 0
    details = []

    if not historical_metrics:
        return {"score": score, "details": "No data for financial strength analysis"}

    latest_item = historical_metrics[-1]
    total_assets = latest_item.total_assets or 0
    total_liabilities = latest_item.total_liabilities or 0
    current_assets = latest_item.current_assets or 0
    current_liabilities = latest_item.current_liabilities or 0

    # 1. Current ratio
    if current_liabilities > 0:
        current_ratio = current_assets / current_liabilities
        if current_ratio >= 2.0:
            score += 2
            details.append(f"Current ratio = {current_ratio:.2f} (>=2.0: solid).")
        elif current_ratio >= 1.5:
            score += 1
            details.append(f"Current ratio = {current_ratio:.2f} (moderately strong).")
        else:
            details.append(f"Current ratio = {current_ratio:.2f} (<1.5: weaker liquidity).")
    else:
        details.append("Cannot compute current ratio (missing or zero current_liabilities).")

    # 2. Debt vs. Assets
    if total_assets > 0:
        debt_ratio = total_liabilities / total_assets
        if debt_ratio < 0.5:
            score += 2
            details.append(f"Debt ratio = {debt_ratio:.2f}, under 0.50 (conservative).")
        elif debt_ratio < 0.8:
            score += 1
            details.append(f"Debt ratio = {debt_ratio:.2f}, somewhat high but could be acceptable.")
        else:
            details.append(f"Debt ratio = {debt_ratio:.2f}, quite high by Graham standards.")
    else:
        details.append("Cannot compute debt ratio (missing total_assets).")

    # 3. Dividend track record
    div_periods = [item.dividends_and_other_cash_distributions for item in historical_metrics if item.dividends_and_other_cash_distributions is not None]
    if div_periods:
        # In many data feeds, dividend outflow is shown as a negative number
        # (money going out to shareholders). We'll consider any negative as 'paid a dividend'.
        div_paid_years = sum(1 for d in div_periods if d < 0)
        if div_paid_years > 0:
            # e.g. if at least half the periods had dividends
            if div_paid_years >= (len(div_periods) // 2 + 1):
                score += 1
                details.append("Company paid dividends in the majority of the reported years.")
            else:
                details.append("Company has some dividend payments, but not most years.")
        else:
            details.append("Company did not pay dividends in these periods.")
    else:
        details.append("No dividend data available to assess payout consistency.")

    return {"score": score, "details": "; ".join(details)}

def analyze_valuation_graham(metrics: FinancialMetrics, historical_metrics: list[FinancialMetrics], market_cap: float) -> dict:
    """
    Core Graham approach to valuation:
    1. Net-Net Check: (Current Assets - Total Liabilities) vs. Market Cap
    2. Graham Number: sqrt(22.5 * EPS * Book Value per Share)
    3. Compare per-share price to Graham Number => margin of safety
    """
    if not historical_metrics or not market_cap or market_cap <= 0:
        return {"score": 0, "details": "Insufficient data to perform valuation"}

    latest = historical_metrics[-1]
    current_assets = latest.current_assets or 0
    total_liabilities = latest.total_liabilities or 0
    book_value_ps = latest.book_value_per_share or 0
    eps = latest.earnings_per_share or 0
    shares_outstanding = latest.outstanding_shares or 0

    details = []
    score = 0

    # 1. Net-Net Check
    #   NCAV = Current Assets - Total Liabilities
    #   If NCAV > Market Cap => historically a strong buy signal
    net_current_asset_value = current_assets - total_liabilities
    if net_current_asset_value > 0 and shares_outstanding > 0:
        net_current_asset_value_per_share = net_current_asset_value / shares_outstanding
        price_per_share = market_cap / shares_outstanding if shares_outstanding else 0

        details.append(f"Net Current Asset Value = {net_current_asset_value:,.2f}")
        details.append(f"NCAV Per Share = {net_current_asset_value_per_share:,.2f}")
        details.append(f"Price Per Share = {price_per_share:,.2f}")

        if net_current_asset_value > market_cap:
            score += 4  # Very strong Graham signal
            details.append("Net-Net: NCAV > Market Cap (classic Graham deep value).")
        else:
            # For partial net-net discount
            if net_current_asset_value_per_share >= (price_per_share * 0.67):
                score += 2
                details.append("NCAV Per Share >= 2/3 of Price Per Share (moderate net-net discount).")
    else:
        details.append("NCAV not exceeding market cap or insufficient data for net-net approach.")

    # 2. Graham Number
    #   GrahamNumber = sqrt(22.5 * EPS * BVPS).
    #   Compare the result to the current price_per_share
    #   If GrahamNumber >> price, indicates undervaluation
    graham_number = None
    if eps > 0 and book_value_ps > 0:
        graham_number = math.sqrt(22.5 * eps * book_value_ps)
        details.append(f"Graham Number = {graham_number:.2f}")
    else:
        details.append("Unable to compute Graham Number (EPS or Book Value missing/<=0).")

    # 3. Margin of Safety relative to Graham Number
    if graham_number and shares_outstanding > 0:
        current_price = market_cap / shares_outstanding
        if current_price > 0:
            margin_of_safety = (graham_number - current_price) / current_price
            details.append(f"Margin of Safety (Graham Number) = {margin_of_safety:.2%}")
            if margin_of_safety > 0.5:
                score += 3
                details.append("Price is well below Graham Number (>=50% margin).")
            elif margin_of_safety > 0.2:
                score += 1
                details.append("Some margin of safety relative to Graham Number.")
            else:
                details.append("Price close to or above Graham Number, low margin of safety.")
        else:
            details.append("Current price is zero or invalid; can't compute margin of safety.")

    return {"score": score, "details": "; ".join(details)}

def generate_graham_output(
    ticker: str,
    analysis_data: dict[str, any]
) -> BenGrahamSignal:
    """Get investment decision from LLM with Graham's principles"""
    template = ChatPromptTemplate.from_messages([
        (
            "system",
            SYSTEM_PROMPT,
        ),
        (
            "human",
            HUMAN_PROMPT,
        ),
    ])

    prompt = template.invoke({"analysis_data": json.dumps(analysis_data, indent=2), "ticker": ticker})

    response = llm.with_structured_output(BenGrahamSignal).invoke(prompt)

    return response