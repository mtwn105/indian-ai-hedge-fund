from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os
from indian_ai_hedge_fund.utils.logging_config import logger

load_dotenv()

api_key = os.getenv("KITE_API_KEY")
api_secret = os.getenv("KITE_API_SECRET")
access_token = os.getenv("KITE_ACCESS_TOKEN")

kite = KiteConnect(api_key=api_key, access_token=access_token)

def get_user_profile() -> str:
    """Get the authenticated user's Zerodha profile information.

    Retrieves details like:
    - User ID
    - User name
    - Email
    - Trading experience
    - Products enabled
    - Order types allowed
    - Exchange memberships
    - Account activation status

    Returns:
        str: A string representation of the user's complete profile information from Zerodha
    """
    logger.info("Entering get_user_profile")
    # Get user profile
    profile = kite.profile()
    logger.info(f"Profile: {profile}")
    logger.info("Exiting get_user_profile")
    return str(profile)


def get_margins(segment: str) -> str:
    """Get the user's available margins and fund details from Zerodha.

    Retrieves information including:
    - Available cash balance
    - Used margin
    - Available margin
    - Opening balance
    - Margin utilized for various segments (equity, commodity, etc)
    - Collateral value
    - Margin categories (SPAN, exposure, etc)

    Args:
        segment (str): The trading segment to get margins for. Valid values are:
            - equity: For equity, mutual funds and bonds
            - commodity: For commodities trading
            If not specified, returns margins for all segments.

    Returns:
        str: A string representation of the complete margins and funds information
    """
    logger.info(f"Entering get_margins with segment: {segment}")
    # Get margins for all segments
    margins = kite.margins(segment=segment)
    logger.info(f"Margins: {margins}")
    logger.info("Exiting get_margins")
    return str(margins)


def get_holdings() -> str:
    """Get the user's portfolio holdings from Zerodha.

    Retrieves detailed information about all securities currently held in the portfolio, including:
    - Trading symbol
    - Exchange
    - ISIN code
    - Product (CNC, MIS, etc.)
    - Average price
    - Last price
    - Quantity
    - PnL (Profit and Loss)
    - Close price
    - Value

    Returns:
        str: A string representation of the complete holdings information
    """
    logger.info("Entering get_holdings")
    holdings = kite.holdings()
    logger.info(f"Holdings: {holdings}")
    logger.info("Exiting get_holdings")
    return holdings


def get_instruments(exchange: str = None) -> list:
    """Fetch the list of tradable instruments available on Zerodha.

    Retrieves a list of all available contracts for trading, including details like:
    - instrument_token
    - exchange_token
    - tradingsymbol
    - name
    - last_price
    - expiry
    - strike
    - tick_size
    - lot_size
    - instrument_type
    - segment
    - exchange

    Args:
        exchange (str, optional): Filter instruments by exchange (e.g., "NSE", "BSE", "NFO").
                                  If None, fetches instruments for all exchanges. Defaults to None.

    Returns:
        list: A list of dictionaries, where each dictionary represents an instrument.
    """
    logger.info(f"Entering get_instruments with exchange: {exchange}")
    try:
        instruments = kite.instruments(exchange=exchange)
        logger.info(f"Successfully fetched {len(instruments)} instruments for exchange: {exchange or 'all'}.")
        logger.info("Exiting get_instruments")
        return instruments
    except Exception as e:
        logger.exception(f"Error fetching instruments for exchange {exchange or 'all'}: {str(e)}")
        raise


def place_order(exchange: str, tradingsymbol: str, transaction_type: str,
                quantity: int, price: float, product: str = "CNC",
                order_type: str = "MARKET", validity: str = "DAY", variety: str = "regular") -> str:
    """Place a new order on Zerodha.

    Args:
        exchange (str): Exchange in which the security is listed (NSE, BSE, NFO, etc)
        tradingsymbol (str): Trading symbol of the security
        transaction_type (str): BUY or SELL
        quantity (int): Number of shares/units to trade
        price (float): Price at which to trade
        product (str, optional): Product code. Defaults to "CNC".
        order_type (str, optional): Type of order (MARKET, LIMIT, etc). Defaults to "MARKET".
        validity (str, optional): Validity of the order. Defaults to "DAY".
        variety (str, optional): Order variety (regular, amo, bo, co). Defaults to "regular".

    Returns:
        str: Order ID of the placed order
    """
    logger.info(f"Entering place_order with params: exchange={exchange}, tradingsymbol={tradingsymbol}, "
               f"transaction_type={transaction_type}, quantity={quantity}, price={price}, product={product}, "
               f"order_type={order_type}, validity={validity}, variety={variety}")

    try:
        order_id = kite.place_order(
            variety=variety,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            product=product,
            order_type=order_type,
            validity=validity
        )
        logger.info(f"Order placed successfully. Order ID: {order_id}")
        return str(order_id)
    except Exception as e:
        logger.exception(f"Error placing order: {str(e)}")
        raise


def get_historical_data(instrument_token: int, from_date: str, to_date: str, interval: str, continuous: bool = False, oi: bool = False) -> list[list[any]]:
    """Fetch historical candle data for a given instrument.

    Provides archived data (up to date as of the time of access) for instruments
    across various exchanges spanning back several years. A historical record is
    presented in the form of a candle (Timestamp, Open, High, Low, Close, Volume, OI).

    Args:
        instrument_token (int): Identifier for the instrument. Obtain this from the
                                instrument list API.
        from_date (str): yyyy-mm-dd hh:mm:ss formatted date indicating the start date of records.
        to_date (str): yyyy-mm-dd hh:mm:ss formatted date indicating the end date of records.
        interval (str): The candle record interval. Possible values are:
                        'minute', 'day', '3minute', '5minute', '10minute',
                        '15minute', '30minute', '60minute'.
        continuous (bool, optional): Pass True to get continuous data for futures contracts.
                                     Defaults to False.
        oi (bool, optional): Pass True to get Open Interest data along with candles.
                             Defaults to False.

    Returns:
        list: A list of candle records. Each record is a list containing:
              [timestamp, open, high, low, close, volume] or
              [timestamp, open, high, low, close, volume, oi] if oi=True.
    """
    logger.info(f"Entering get_historical_data with params: instrument_token={instrument_token}, "
               f"from_date={from_date}, to_date={to_date}, interval={interval}, "
               f"continuous={continuous}, oi={oi}")

    try:
        historical_data = kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=interval,
            continuous=continuous,
            oi=oi
        )
        logger.info(f"Successfully fetched historical data for instrument {instrument_token}.")
        logger.debug(f"Historical data sample: {historical_data[:5]}") # Log a small sample
        logger.info("Exiting get_historical_data")
        return historical_data
    except Exception as e:
        logger.exception(f"Error fetching historical data for instrument {instrument_token}: {str(e)}")
        raise






