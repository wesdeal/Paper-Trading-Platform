# define worker settings and job function

from app.redis_client import redis_client
from app.services.market_data import fetch_quote
from arq import cron
from arq.connections import RedisSettings
from app.config import settings
import time


WINDOW_SECONDS = 3600 # "active" tickers = requested in last hour
MAX_TICKERS = 100
TTL = 360
async def refresh_quotes(ctx):
    # every 5 minutes, call run get_quote_from_cache on all stocks in watch list
    # with updated TTL
    
    now = time.time()
    cutoff = now - WINDOW_SECONDS

    # retrieve all tickers in the watchlist to refresh
    tickers = await redis_client.zrangebyscore("watchlist", cutoff, "+inf")
    
    for ticker in tickers:
        price = await fetch_quote(ticker)
        if price is None:
            continue
        key = f"quote:{ticker}"
        await redis_client.set(key, str(price), ex=TTL)
    
    # remove tickers outside most recent 100 if more than 100 req in last hour
    await redis_client.zremrangebyrank("watchlist", 0, -(MAX_TICKERS + 1))
        

    


""" 
    we dont want the worker to just refresh everything in the cache
 """
class WorkerSettings:
    functions = [refresh_quotes]
    cron_jobs = [cron(refresh_quotes, minute={0,5,10,15,20,25,30,35,40,45,50,55})]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)




