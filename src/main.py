from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db

app = FastAPI(title="Asset Management System")

@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        # Verify database connection
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}
