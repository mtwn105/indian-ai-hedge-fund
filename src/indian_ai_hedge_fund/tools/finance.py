import yfinance as yf
from pydantic import BaseModel
import datetime
from indian_ai_hedge_fund.utils.logging_config import logger
import warnings
import pandas as pd

# Suppress specific FutureWarnings from yfinance
warnings.filterwarnings("ignore", category=FutureWarning, module='yfinance.utils')

class FinancialMetrics(BaseModel):
    capital_expenditure: float | None = None
    depreciation_and_amortization: float | None = None
    net_income: float | None = None
    outstanding_shares: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    dividends_and_other_cash_distributions: float | None = None
    issuance_or_purchase_of_equity_shares: float | None = None
    return_on_equity: float | None = None
    debt_to_equity_ratio: float | None = None
    operating_margin: float | None = None
    current_ratio: float | None = None
    market_cap: float | None = None
    period: datetime.datetime | None = None
    # Added fields for Graham analysis
    earnings_per_share: float | None = None
    book_value_per_share: float | None = None
    price_to_earnings_ratio: float | None = None
    price_to_book_ratio: float | None = None
    working_capital: float | None = None
    long_term_debt: float | None = None
    current_assets: float | None = None
    current_liabilities: float | None = None

def _fetch_and_calculate_latest_metrics(ticker_symbol: str) -> FinancialMetrics | None:
    """Helper function to fetch and calculate latest metrics for a given ticker symbol."""
    try:
        ticker = yf.Ticker(ticker_symbol)
        income_stmt = ticker.financials
        balance_sheet = ticker.balance_sheet
        cashflow = ticker.cashflow
        info = ticker.info

        # Check if dataframes are empty or malformed
        if income_stmt.empty or balance_sheet.empty or cashflow.empty or not info:
             logger.warning(f"Incomplete data received for ticker: {ticker_symbol}")
             return None

        def safe_get(df, key):
            if df.empty:
                return None
            for idx in df.index:
                if key.lower() in idx.lower():
                    try:
                        # Handle potential MultiIndex or Series issues
                        if isinstance(df.loc[idx], pd.Series):
                           return df.loc[idx].iloc[0]
                        else:
                           return df.loc[idx]
                    except IndexError:
                        logger.warning(f"IndexError accessing {key} for {ticker_symbol}. Data shape: {df.loc[idx].shape}")
                        return None
                    except Exception as e:
                        logger.warning(f"Unexpected error accessing {key} for {ticker_symbol}: {e}")
                        return None
            return None

        net_income = safe_get(income_stmt, "Net Income") or safe_get(income_stmt, "Net Income From Continuing Operations")
        total_assets = safe_get(balance_sheet, "Total Assets")
        total_liabilities = safe_get(balance_sheet, "Total Liab")
        current_assets = safe_get(balance_sheet, "Current Assets")
        current_liabilities = safe_get(balance_sheet, "Current Liabilities")
        long_term_debt = safe_get(balance_sheet, "Long Term Debt")
        working_capital = current_assets - current_liabilities if current_assets is not None and current_liabilities is not None else None

        # Calculate per share metrics
        shares = info.get("sharesOutstanding")
        if shares is None or shares == 0:
             logger.warning(f"Shares outstanding not available or zero for {ticker_symbol}")
             shares = None # Ensure shares is None if invalid

        eps = net_income / shares if net_income is not None and shares is not None else None
        book_value = total_assets - total_liabilities if total_assets is not None and total_liabilities is not None else None
        bvps = book_value / shares if book_value is not None and shares is not None else None


        # Calculate price ratios
        price = info.get("currentPrice") or info.get("previousClose") # Use previous close as fallback
        if price is None:
            logger.warning(f"Current price not available for {ticker_symbol}")

        pe_ratio = price / eps if price is not None and eps is not None and eps != 0 else None
        pb_ratio = price / bvps if price is not None and bvps is not None and bvps != 0 else None

        # Ratios
        return_on_equity = (net_income / book_value) if net_income is not None and book_value is not None and book_value != 0 else None
        debt_to_equity_ratio = (total_liabilities / book_value) if total_liabilities is not None and book_value is not None and book_value != 0 else None
        current_ratio = (current_assets / current_liabilities) if current_assets is not None and current_liabilities is not None and current_liabilities != 0 else None
        operating_margin = info.get("operatingMargins")  # Already in decimal
        market_cap = info.get("marketCap")

        # Cashflow items
        capital_expenditure = safe_get(cashflow, "Capital Expenditure")
        depreciation_and_amortization = safe_get(cashflow, "Depreciation And Amortization")
        dividends_paid = safe_get(cashflow, "Cash Dividends Paid")
        issuance_stock = safe_get(cashflow, "Issuance Of Capital Stock")


        return FinancialMetrics(
            capital_expenditure=capital_expenditure,
            depreciation_and_amortization=depreciation_and_amortization,
            net_income=net_income,
            outstanding_shares=shares,
            total_assets=total_assets,
            total_liabilities=total_liabilities,
            dividends_and_other_cash_distributions=dividends_paid,
            issuance_or_purchase_of_equity_shares=issuance_stock,
            return_on_equity=return_on_equity,
            debt_to_equity_ratio=debt_to_equity_ratio,
            operating_margin=operating_margin,
            current_ratio=current_ratio,
            market_cap=market_cap,
            # period= # Latest doesn't have a specific period from yfinance structure here
            earnings_per_share=eps,
            book_value_per_share=bvps,
            price_to_earnings_ratio=pe_ratio,
            price_to_book_ratio=pb_ratio,
            working_capital=working_capital,
            long_term_debt=long_term_debt,
            current_assets=current_assets,
            current_liabilities=current_liabilities
        )
    except Exception as e:
        logger.error(f"Error fetching or processing latest data for {ticker_symbol}: {e}")
        return None


def get_latest_financial_metrics(ticker_symbol: str) -> FinancialMetrics | None:
    """
    Fetches the latest available financial metrics for a given stock ticker.
    Tries with .NS (NSE) suffix first, then .BO (BSE) if .NS fails.
    """
    # Try with .NS suffix
    if not ticker_symbol.endswith((".NS", ".BO")):
        ticker_ns = f"{ticker_symbol}.NS"
    else:
        ticker_ns = ticker_symbol # Assume provided suffix is intended

    logger.info(f"Attempting to fetch latest data for {ticker_ns}")
    metrics = _fetch_and_calculate_latest_metrics(ticker_ns)

    if metrics:
        return metrics

    # If .NS failed or returned None, and the original didn't end with .BO, try .BO
    if not ticker_symbol.endswith(".BO"):
        ticker_bo = f"{ticker_symbol}.BO"
        logger.info(f"Fetching with {ticker_ns} failed or returned no data, trying {ticker_bo}")
        metrics = _fetch_and_calculate_latest_metrics(ticker_bo)
        if metrics:
            return metrics

    logger.warning(f"Could not retrieve valid latest financial data for {ticker_symbol} using .NS or .BO.")
    return None


def _fetch_and_calculate_historical_metrics(ticker_symbol: str, periods: int = 5) -> list[FinancialMetrics]:
    """Helper function to fetch and calculate historical metrics for a given ticker symbol."""
    results = []
    try:
        ticker = yf.Ticker(ticker_symbol)

        # Get annual data
        income_stmt = ticker.get_financials(freq="yearly")
        balance_sheet = ticker.get_balance_sheet(freq="yearly")
        cashflow = ticker.get_cashflow(freq="yearly")
        info = ticker.info # Fetch info once

        # Check for empty dataframes early
        if income_stmt.empty or balance_sheet.empty or cashflow.empty:
            logger.warning(f"Empty historical dataframes for {ticker_symbol}.")
            return []

        logger.debug(f"Income Statement columns for {ticker_symbol}: {income_stmt.columns}")
        logger.debug(f"Balance Sheet columns for {ticker_symbol}: {balance_sheet.columns}")
        logger.debug(f"Cashflow columns for {ticker_symbol}: {cashflow.columns}")
        # logger.debug(f"Info for {ticker_symbol}: {info}") # Can be very verbose


        # Ensure alignment and limit periods across all dataframes
        common_cols = income_stmt.columns.intersection(balance_sheet.columns).intersection(cashflow.columns)
        common_cols = sorted(common_cols, reverse=True)[:periods] # Get latest 'periods' common columns

        if not common_cols:
             logger.warning(f"No common historical periods found for {ticker_symbol}.")
             return []

        income_stmt = income_stmt[common_cols]
        balance_sheet = balance_sheet[common_cols]
        cashflow = cashflow[common_cols]


        def safe_get_hist(df, key):
            if df.empty:
                 return [None] * len(common_cols)
            for idx in df.index:
                if key.lower() in idx.lower():
                     # Ensure the row exists for the common columns
                     if idx in df.index:
                         return df.loc[idx, common_cols].tolist()
                     else:
                         logger.warning(f"Key '{key}' (row '{idx}') not found in dataframe for {ticker_symbol} with common columns.")
                         return [None] * len(common_cols)
            logger.warning(f"Key '{key}' not found in index for {ticker_symbol}.")
            return [None] * len(common_cols)


        # Get metrics across all periods
        net_income = safe_get_hist(income_stmt, "NetIncome") or safe_get_hist(income_stmt, "NetIncomeContinuousOperations")
        total_assets = safe_get_hist(balance_sheet, "TotalAssets")
        total_liabilities = safe_get_hist(balance_sheet, "TotalLiab") or safe_get_hist(balance_sheet, "TotalLiabilities") or safe_get_hist(balance_sheet, "TotalLiabilitiesNetMinorityInterest")
        current_assets = safe_get_hist(balance_sheet, "CurrentAssets")
        current_liabilities = safe_get_hist(balance_sheet, "CurrentLiabilities")
        long_term_debt = safe_get_hist(balance_sheet, "LongTermDebt")
        capital_expenditure = safe_get_hist(cashflow, "CapitalExpenditure")
        depreciation = safe_get_hist(cashflow, "DepreciationAndAmortization")
        dividends_paid = safe_get_hist(cashflow, "CashDividendsPaid")


        shares = info.get("sharesOutstanding") # Use single value for historical calculations as well
        if shares is None or shares == 0:
            logger.warning(f"Shares outstanding not available or zero for {ticker_symbol}, historical per-share metrics will be None.")
            shares = None


        for i, period_ts in enumerate(common_cols):
             # Calculate derived metrics for the specific period
             ta = total_assets[i]
             tl = total_liabilities[i]
             ca = current_assets[i]
             cl = current_liabilities[i]
             ni = net_income[i]
             ltd = long_term_debt[i]
             capex = capital_expenditure[i]
             depr = depreciation[i]
             divp = dividends_paid[i]


             se = ta - tl if ta is not None and tl is not None else None
             roe = (ni / se) if ni is not None and se is not None and se != 0 else None
             de = (tl / se) if tl is not None and se is not None and se != 0 else None
             cr = (ca / cl) if ca is not None and cl is not None and cl != 0 else None
             wc = ca - cl if ca is not None and cl is not None else None

             # Calculate per share metrics
             eps = ni / shares if ni is not None and shares is not None else None
             bvps = se / shares if se is not None and shares is not None else None

             # Convert pandas timestamp to datetime.datetime
             period_dt = period_ts.to_pydatetime() if hasattr(period_ts, 'to_pydatetime') else None


             results.append(FinancialMetrics(
                period=period_dt,
                capital_expenditure=capex,
                depreciation_and_amortization=depr,
                net_income=ni,
                total_assets=ta,
                total_liabilities=tl,
                dividends_and_other_cash_distributions=divp, # Renamed field
                # issuance_or_purchase_of_equity_shares= # Not reliably available in annual cashflow across periods easily
                return_on_equity=roe,
                debt_to_equity_ratio=de, # Renamed field
                # operating_margin= # Not typically in annual historical financials this way
                current_ratio=cr,
                # market_cap= # Market cap changes daily, not tied to annual report period
                earnings_per_share=eps,
                book_value_per_share=bvps,
                # price_to_earnings_ratio= # Needs price for that specific date, harder to get reliably
                # price_to_book_ratio= # Needs price for that specific date
                working_capital=wc,
                long_term_debt=ltd,
                current_assets=ca,
                current_liabilities=cl,
                # outstanding_shares = shares # Add if needed, but it's constant across history here
             ))

        # Add latest market data to the most recent historical period's entry if available
        if results:
             price = info.get("currentPrice") or info.get("previousClose")
             if price and results[0].earnings_per_share is not None and results[0].earnings_per_share != 0:
                 results[0].price_to_earnings_ratio = price / results[0].earnings_per_share
             if price and results[0].book_value_per_share is not None and results[0].book_value_per_share != 0:
                 results[0].price_to_book_ratio = price / results[0].book_value_per_share

             results[0].outstanding_shares = shares # Add latest shares outstanding
             results[0].operating_margin = info.get("operatingMargins") # Add latest op margin
             results[0].market_cap = info.get("marketCap") # Add latest market cap


    except Exception as e:
        logger.error(f"Error fetching or processing historical data for {ticker_symbol}: {e}")
        # results remains an empty list

    return results


def get_historical_financial_metrics(ticker_symbol: str, periods: int = 5) -> list[FinancialMetrics]:
    """
    Fetches historical annual financial metrics for a given stock ticker for the specified number of periods.
    Tries with .NS (NSE) suffix first, then .BO (BSE) if .NS fails.
    """
    # Try with .NS suffix
    if not ticker_symbol.endswith((".NS", ".BO")):
        ticker_ns = f"{ticker_symbol}.NS"
    else:
        ticker_ns = ticker_symbol # Assume provided suffix is intended

    logger.info(f"Attempting to fetch historical data for {ticker_ns}")
    metrics_list = _fetch_and_calculate_historical_metrics(ticker_ns, periods)

    if metrics_list: # Check if list is not empty
        return metrics_list

    # If .NS failed or returned [], and the original didn't end with .BO, try .BO
    if not ticker_symbol.endswith(".BO"):
        ticker_bo = f"{ticker_symbol}.BO"
        logger.info(f"Fetching historical with {ticker_ns} failed or returned no data, trying {ticker_bo}")
        metrics_list = _fetch_and_calculate_historical_metrics(ticker_bo, periods)
        if metrics_list:
            return metrics_list

    logger.warning(f"Could not retrieve valid historical financial data for {ticker_symbol} using .NS or .BO.")
    return [] # Return empty list if both fail