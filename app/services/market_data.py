# talk to external api :: yfinace
# knows nothing about redis, keep separate

from decimal import Decimal


from app.config import settings
import httpx

FINN_API_KEY = settings.finn_api_key





#debugging purposes only
def print_price():
#debugging purposes only
    ticker = "AAPL"
    url = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINN_API_KEY}"

    response = httpx.get(url)
    data = response.json()

    current_price = data.get("c")
    print(f"The current price of {ticker} is ${current_price}")



async def  fetch_quote(ticker: str) -> Decimal | None:
    # return current/last price and ticker of stock 
    # raw API call, no cache

    async with httpx.AsyncClient() as client:
        r = await client.get("https://finnhub.io/api/v1/quote",
                          params={"symbol": ticker, "token": settings.finn_api_key})
    data = r.json()
    print(r)
    if data["c"] == 0:
        return None
    price = str(data["c"])
    return Decimal(price)

    # this function is called if a quote is not found in the redis cache.
    # this must get added to redis cache 
    


