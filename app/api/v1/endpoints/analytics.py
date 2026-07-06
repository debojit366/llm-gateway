from fastapi import APIRouter
from app.db.mongo import db_helper 

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard():
    db = getattr(db_helper, "db", None)
    
    if db is None:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "status": "Database client not initialized"
        }

    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "total_tokens": {"$sum": "$tokens_used"},
                "total_cost": {"$sum": "$cost_usd"}
            }
        }
    ]
    
    try:
        cursor = db.logs.aggregate(pipeline)  
        result = await cursor.to_list(length=1)
        
        if not result:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
            
        return {
            "total_requests": result[0]["total_requests"],
            "total_tokens": result[0]["total_tokens"],
            "total_cost": round(result[0]["total_cost"], 8)
        }
    except Exception as e:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "error": str(e)
        }