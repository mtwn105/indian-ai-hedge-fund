from kiteconnect import KiteConnect
from dotenv import load_dotenv
import os
import logging

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
    logging.info("Entering get_user_profile")
    # Get user profile
    profile = kite.profile()
    logging.info("Profile: %s", profile)
    logging.info("Exiting get_user_profile")
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
    logging.info("Entering get_margins with segment: %s", segment)
    # Get margins for all segments
    margins = kite.margins(segment=segment)
    logging.info("Margins: %s", margins)
    logging.info("Exiting get_margins")
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
    logging.info("Entering get_holdings")
    holdings = kite.holdings()
    logging.info("Holdings: %s", holdings)
    logging.info("Exiting get_holdings")
    return holdings


def get_positions() -> str:
    """Get the user's current positions from Zerodha.

    Retrieves information about all open positions, including:
    - Day positions
    - Net positions
    - Trading symbol
    - Exchange
    - Product type
    - Quantity
    - Average price
    - Last price
    - PnL (Profit and Loss)
    - Overnight quantity
    - Multiplier

    Returns:
        str: A string representation of the complete positions information
    """
    logging.info("Entering get_positions")
    positions = kite.positions()
    logging.info("Positions: %s", positions)
    logging.info("Exiting get_positions")
    return str(positions)


def get_orders() -> str:
    """Get all orders placed for the day.

    Retrieves detailed information about all orders placed during the current day, including:
    - Order ID
    - Exchange order ID
    - Parent order ID (for bracket orders)
    - Status of the order (COMPLETE, REJECTED, CANCELLED, etc)
    - Exchange
    - Trading symbol
    - Order type (MARKET, LIMIT, etc)
    - Transaction type (BUY or SELL)
    - Product code (CNC, MIS, etc)
    - Quantity
    - Price
    - Trigger price (for SL and SL-M orders)
    - Average price
    - Filled quantity
    - Pending quantity
    - Order timestamp
    - Exchange timestamp
    - Order variety (regular, amo, bo, co, etc)

    Returns:
        str: A string representation of all orders for the day
    """
    logging.info("Entering get_orders")
    orders = kite.orders()
    logging.info("Orders: %s", orders)
    logging.info("Exiting get_orders")
    return str(orders)


def get_order_history(order_id: str) -> str:
    """Get history of an order.

    Retrieves detailed information about all states an order has gone through, including:
    - Order ID
    - Exchange order ID
    - Status of the order at each state (OPEN, COMPLETE, REJECTED, CANCELLED, etc)
    - Filled quantity at each state
    - Pending quantity at each state
    - Average price at each state
    - Exchange update timestamps

    Args:
        order_id (str): ID of the order whose history is to be retrieved

    Returns:
        str: A string representation of the complete order history
    """
    logging.info("Entering get_order_history with order_id: %s", order_id)
    history = kite.order_history(order_id)
    logging.info("Order history: %s", history)
    logging.info("Exiting get_order_history")
    return str(history)


def get_order_trades(order_id: str) -> str:
    """Get trades generated by an order.

    An order can be executed in multiple trades. Use this to get all trades linked to an order.

    Args:
        order_id (str): ID of the order whose trades are to be retrieved

    Returns:
        str: A string representation of all trades for the given order
    """
    logging.info("Entering get_order_trades with order_id: %s", order_id)
    trades = kite.order_trades(order_id)
    logging.info("Order trades: %s", trades)
    logging.info("Exiting get_order_trades")
    return str(trades)


def place_order(exchange: str, tradingsymbol: str, transaction_type: str,
                quantity: int, price: float, product: str = "CNC",
                order_type: str = "MARKET", validity: str = "DAY", variety: str = "regular") -> str:
    """Place a new order on Zerodha.

    Args:
        exchange (str): Exchange in which the security is listed (NSE, BSE, NFO, etc)
        tradingsymbol (str): Trading symbol of the security (RELIANCE, INFY, etc)
        transaction_type (str): Transaction type (BUY or SELL)
        quantity (int): Order quantity
        price (float, optional): Order price for LIMIT orders
        product (str, optional): Product code (CNC, MIS, etc). Default is CNC (delivery).
        order_type (str, optional): Order type (MARKET, LIMIT, etc). Default is MARKET.
        validity (str, optional): Order validity (DAY, IOC, etc). Default is DAY.
        variety (str, optional): Order variety (regular, amo, bo, co, etc). Default is regular.
    Returns:
        str: Order ID of the placed order
    """
    logging.info(f"Entering place_order: exchange={exchange}, symbol={tradingsymbol}, type={transaction_type}, qty={quantity}, price={price}, product={product}, order_type={order_type}")
    try:
        order_id = kite.place_order(
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            product=product,
            order_type=order_type,
            validity=validity,
            variety=variety
        )
        logging.info("Order placed. ID: %s", order_id)
        return f"Order placed successfully. Order ID: {order_id}"
    except Exception as e:
        logging.error("Order placement failed: %s", str(e))
        return f"Order placement failed: {str(e)}"


def modify_order(order_id: str, quantity: int,price: float, order_type: str,
                trigger_price: float, validity: str) -> str:
    """Modify an existing order.

    Args:
        order_id (str): ID of the order to be modified
        quantity (int, optional): New order quantity
        price (float, optional): New order price
        order_type (str, optional): New order type (LIMIT, SL, SL-M, MARKET)
        trigger_price (float, optional): New trigger price for SL and SL-M orders
        validity (str, optional): New validity (DAY, IOC)

    Returns:
        str: Order ID of the modified order
    """
    logging.info(f"Entering modify_order: order_id={order_id}, quantity={quantity}, price={price}, order_type={order_type}")
    try:
        order_id_resp = kite.modify_order(
            order_id=order_id,
            quantity=quantity,
            price=price,
            order_type=order_type,
            trigger_price=trigger_price,
            validity=validity
        )
        logging.info("Order modified. ID: %s", order_id_resp)
        return f"Order modified successfully. Order ID: {order_id_resp}"
    except Exception as e:
        logging.error("Order modification failed: %s", str(e))
        return f"Order modification failed: {str(e)}"


def cancel_order(order_id: str, variety: str = "regular") -> str:
    """Cancel an order.

    Args:
        variety (str): Variety of the order to be cancelled (regular, amo, bo, co, etc). Default is regular.
        order_id (str): ID of the order to be cancelled

    Returns:
        str: Order ID of the cancelled order
    """
    logging.info(f"Entering cancel_order: order_id={order_id}")
    try:
        order_id_resp = kite.cancel_order(variety=variety, order_id=order_id)
        logging.info("Order cancelled. ID: %s", order_id_resp)
        return f"Order cancelled successfully. Order ID: {order_id_resp}"
    except Exception as e:
        logging.error("Order cancellation failed: %s", str(e))
        return f"Order cancellation failed: {str(e)}"





