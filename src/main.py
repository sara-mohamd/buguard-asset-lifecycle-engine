from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.api.v1.router import api_router

from fastapi.responses import RedirectResponse

app = FastAPI(title="Asset Management System")

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

# Include the API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
