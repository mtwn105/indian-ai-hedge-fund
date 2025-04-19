import yfinance as yf
from pydantic import BaseModel
import datetime
from indian_ai_hedge_fund.utils.logging_config import logger

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

def get_latest_financial_metrics(ticker_symbol: str) -> FinancialMetrics:

    if not ticker_symbol.endswith(".NS"):
        ticker_symbol = f"{ticker_symbol}.NS"

    ticker = yf.Ticker(ticker_symbol)
    income_stmt = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow
    info = ticker.info

    def safe_get(df, key):
        for idx in df.index:
            if key.lower() in idx.lower():
                return df.loc[idx].iloc[0]
        return None

    net_income = safe_get(income_stmt, "Net Income") or safe_get(income_stmt, "Net Income From Continuing Operations")
    total_assets = safe_get(balance_sheet, "Total Assets")
    total_liabilities = safe_get(balance_sheet, "Total Liab")
    current_assets = safe_get(balance_sheet, "Current Assets")
    current_liabilities = safe_get(balance_sheet, "Current Liabilities")
    long_term_debt = safe_get(balance_sheet, "Long Term Debt")
    working_capital = current_assets - current_liabilities if current_assets and current_liabilities else None

    # Calculate per share metrics
    shares = info.get("sharesOutstanding")
    eps = net_income / shares if net_income and shares else None
    bvps = (total_assets - total_liabilities) / shares if total_assets and total_liabilities and shares else None

    # Calculate price ratios
    price = info.get("currentPrice")
    pe_ratio = price / eps if price and eps and eps != 0 else None
    pb_ratio = price / bvps if price and bvps and bvps != 0 else None

    # Ratios
    return_on_equity = (net_income / (total_assets - total_liabilities)) if net_income and (total_assets - total_liabilities) else None
    debt_to_equity_ratio = (total_liabilities / (total_assets - total_liabilities)) if total_liabilities and (total_assets - total_liabilities) else None
    current_ratio = (current_assets / current_liabilities) if current_assets and current_liabilities else None
    operating_margin = info.get("operatingMargins")  # Already in decimal
    market_cap = info.get("marketCap")

    return FinancialMetrics(
        capital_expenditure=safe_get(cashflow, "Capital Expenditure"),
        depreciation_and_amortization=safe_get(cashflow, "Depreciation And Amortization"),
        net_income=net_income,
        outstanding_shares=shares,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        dividends_and_other_cash_distributions=safe_get(cashflow, "Cash Dividends Paid"),
        issuance_or_purchase_of_equity_shares=safe_get(cashflow, "Issuance Of Capital Stock"),
        return_on_equity=return_on_equity,
        debt_to_equity_ratio=debt_to_equity_ratio,
        operating_margin=operating_margin,
        current_ratio=current_ratio,
        market_cap=market_cap,
        earnings_per_share=eps,
        book_value_per_share=bvps,
        price_to_earnings_ratio=pe_ratio,
        price_to_book_ratio=pb_ratio,
        working_capital=working_capital,
        long_term_debt=long_term_debt,
        current_assets=current_assets,
        current_liabilities=current_liabilities
    )


def get_historical_financial_metrics(ticker_symbol: str, periods: int = 5) -> list[FinancialMetrics]:

    if not ticker_symbol.endswith(".NS"):
        ticker_symbol = f"{ticker_symbol}.NS"

    ticker = yf.Ticker(ticker_symbol)

    # Get annual data instead of quarterly
    income_stmt = ticker.get_financials(freq="yearly")
    balance_sheet = ticker.get_balance_sheet(freq="yearly")
    cashflow = ticker.get_cashflow(freq="yearly")
    info = ticker.info

    logger.debug(f"Income Statement: {income_stmt}")
    logger.debug(f"Balance Sheet: {balance_sheet}")
    logger.debug(f"Cashflow: {cashflow}")
    logger.debug(f"Info: {info}")

    # Limit to last 5 periods if available
    income_stmt = income_stmt.iloc[:, :periods] if income_stmt.shape[1] >= periods else income_stmt
    balance_sheet = balance_sheet.iloc[:, :periods] if balance_sheet.shape[1] >= periods else balance_sheet
    cashflow = cashflow.iloc[:, :periods] if cashflow.shape[1] >= periods else cashflow

    def safe_get(df, key):
        for idx in df.index:
            if key.lower() in idx.lower():
                return df.loc[idx].tolist()  # Return all periods as a list
        return [None] * len(df.columns)  # Return appropriate number of Nones

    # Get metrics across all periods
    net_income = safe_get(income_stmt, "NetIncome") or safe_get(income_stmt, "NetIncomeContinuousOperations")
    total_assets = safe_get(balance_sheet, "TotalAssets")
    total_liabilities = safe_get(balance_sheet, "TotalLiab") or safe_get(balance_sheet, "TotalLiabilities") or safe_get(balance_sheet, "TotalLiabilitiesNetMinorityInterest")
    current_assets = safe_get(balance_sheet, "CurrentAssets")
    current_liabilities = safe_get(balance_sheet, "CurrentLiabilities")
    long_term_debt = safe_get(balance_sheet, "LongTermDebt")

    # Calculate metrics for each period
    periods = income_stmt.columns.tolist()

    logger.debug(f"Periods: {periods}")

    results = []

    for i in range(len(periods)):
        # Calculate derived metrics
        se = total_assets[i] - total_liabilities[i] if total_assets[i] and total_liabilities[i] else None
        roe = (net_income[i] / se) if net_income[i] and se else None
        de = (total_liabilities[i] / se) if total_liabilities[i] and se else None
        cr = (current_assets[i] / current_liabilities[i]) if current_assets[i] and current_liabilities[i] else None
        wc = current_assets[i] - current_liabilities[i] if current_assets[i] and current_liabilities[i] else None

        # Calculate per share metrics
        shares = info.get("sharesOutstanding")
        eps = net_income[i] / shares if net_income[i] and shares else None
        bvps = se / shares if se and shares else None

        results.append(FinancialMetrics(
            period=periods[i],
            capital_expenditure=safe_get(cashflow, "CapitalExpenditure")[i],
            depreciation_and_amortization=safe_get(cashflow, "DepreciationAndAmortization")[i],
            net_income=net_income[i],
            total_assets=total_assets[i],
            total_liabilities=total_liabilities[i],
            dividends_paid=safe_get(cashflow, "CashDividendsPaid")[i],
            return_on_equity=roe,
            debt_to_equity=de,
            current_ratio=cr,
            current_assets=current_assets[i],
            current_liabilities=current_liabilities[i],
            working_capital=wc,
            long_term_debt=long_term_debt[i],
            earnings_per_share=eps,
            book_value_per_share=bvps
        ))

    # Add current market data (single values)
    price = info.get("currentPrice")
    if price and results[0].earnings_per_share:
        results[0].price_to_earnings_ratio = price / results[0].earnings_per_share
    if price and results[0].book_value_per_share:
        results[0].price_to_book_ratio = price / results[0].book_value_per_share

    results[0].outstanding_shares = info.get("sharesOutstanding")
    results[0].operating_margin = info.get("operatingMargins")
    results[0].market_cap = info.get("marketCap")

    return results