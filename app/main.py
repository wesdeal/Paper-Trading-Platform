from fastapi import FastAPI

app = FastAPI(title="Paper Trading Platform")

@app.get("/health")
async def health():
    return {"status": "ok"}