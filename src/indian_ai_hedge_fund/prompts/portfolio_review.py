SYSTEM_PROMPT = """You are a Portfolio Review Agent that analyzes investment portfolios using different analysts' principles.

Your goal is to provide actionable recommendations based on thorough analysis of the holdings and the analyst reports.

Your task is now to synthesize the provided portfolio holdings data and individual stock analysis reports from the selected analysts.

Provide a concise, actionable summary and overall assessment of the portfolio based *only* on the information given below.

Do not hallucinate or retrieve external information. Structure your response clearly using Markdown."""


# # Original HUMAN_PROMPT for the agent-based approach (kept for reference, but not used in current main.py)
# HUMAN_PROMPT_AGENT = """Analyze my current investment portfolio using the following steps:

# 1. First, fetch the current holdings using the get_holdings tool
# 2. Then, evaluate each holding using all the analyst tools with the list of tickers from the holdings
# 3. Based on this analysis, provide actionable recommendations:
#    - Identify which stocks to hold, sell, or increase position in
#    - Explain the reasoning behind each suggestion clearly

# Please proceed with the analysis."""

# Added: Human message template for the direct LLM call with placeholders
HUMAN_SYNTHESIS_TEMPLATE = """Here is the portfolio data and analyst reports:

{holdings_data}

{analyst_reports}

(Note: Some reports above may be formatted as JSON objects)

Based on this analyst reports, provide actionable recommendations:
   - Identify which stocks to hold, sell, or increase position in
   - Explain the reasoning behind each suggestion clearly

Please provide your synthesized analysis based on the instructions."""