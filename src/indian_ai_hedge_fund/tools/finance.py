import yfinance as yf
from pydantic import BaseModel
import datetime
import logging

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

    # print("Balance Sheet Index Items:")
    # for idx in balance_sheet.index:
    #     print(f"- {idx}")

    # Calculate Shareholder Equity
    shareholder_equity = total_assets - total_liabilities if total_assets and total_liabilities else None

    # Ratios
    return_on_equity = (net_income / shareholder_equity) if net_income and shareholder_equity else None
    debt_to_equity_ratio = (total_liabilities / shareholder_equity) if total_liabilities and shareholder_equity else None
    current_ratio = (current_assets / current_liabilities) if current_assets and current_liabilities else None
    operating_margin = info.get("operatingMargins")  # Already in decimal
    market_cap = info.get("marketCap")

    return FinancialMetrics(
        capital_expenditure=safe_get(cashflow, "Capital Expenditure"),
        depreciation_and_amortization=safe_get(cashflow, "Depreciation And Amortization"),
        net_income=net_income,
        outstanding_shares=info.get("sharesOutstanding"),
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        dividends_and_other_cash_distributions=safe_get(cashflow, "Cash Dividends Paid"),
        issuance_or_purchase_of_equity_shares=safe_get(cashflow, "Issuance Of Capital Stock"),
        return_on_equity=return_on_equity,
        debt_to_equity_ratio=debt_to_equity_ratio,
        operating_margin=operating_margin,
        current_ratio=current_ratio,
        market_cap=market_cap
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

    logging.debug("Income Statement: %s", income_stmt)
    logging.debug("Balance Sheet: %s", balance_sheet)
    logging.debug("Cashflow: %s", cashflow)
    logging.debug("Info: %s", info)

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

    # Calculate metrics for each period
    periods = income_stmt.columns.tolist()

    logging.debug("Periods: %s", periods)

    results = []

    for i in range(len(periods)):
        # Calculate derived metrics
        se = total_assets[i] - total_liabilities[i] if total_assets[i] and total_liabilities[i] else None
        roe = (net_income[i] / se) if net_income[i] and se else None
        de = (total_liabilities[i] / se) if total_liabilities[i] and se else None
        cr = (current_assets[i] / current_liabilities[i]) if current_assets[i] and current_liabilities[i] else None

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
        ))

    # Add current market data (single values)
    results[0].outstanding_shares = info.get("sharesOutstanding")
    results[0].operating_margin = info.get("operatingMargins")
    results[0].market_cap = info.get("marketCap")

    return results