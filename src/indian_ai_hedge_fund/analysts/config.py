from typing import Dict, Tuple, Callable
from indian_ai_hedge_fund.analysts.warren_buffet import warren_buffett_analyst
from indian_ai_hedge_fund.analysts.ben_graham import ben_graham_analyst
from indian_ai_hedge_fund.analysts.technical import technical_analyst
from indian_ai_hedge_fund.utils.logging_config import logger

def get_analysts() -> Dict[str, Tuple[str, Callable]]:
    """Get available analysts with their display names and functions"""
    logger.debug("Getting available analysts")
    analysts = {
        'Warren Buffett': ('Warren Buffett', warren_buffett_analyst),
        'Benjamin Graham': ('Benjamin Graham', ben_graham_analyst),
        'Technical Analyst': ('Technical Analyst', technical_analyst),
        # Add new analysts here
    }
    logger.debug(f"Found {len(analysts)} analysts")
    return analysts