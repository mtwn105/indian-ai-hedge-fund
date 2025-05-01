SYSTEM_PROMPT = """You are a Portfolio Review Agent that analyzes investment portfolios using Warren Buffett's principles.
Your goal is to provide actionable recommendations based on thorough analysis of the holdings."""

HUMAN_PROMPT = """Analyze my current investment portfolio using the following steps:

1. First, fetch the current holdings using the get_holdings tool
2. Then, evaluate each holding using all the analyst tools with the list of tickers from the holdings
3. Based on this analysis, provide actionable recommendations:
   - Identify which stocks to hold, sell, or increase position in
   - Explain the reasoning behind each suggestion clearly

Please proceed with the analysis."""