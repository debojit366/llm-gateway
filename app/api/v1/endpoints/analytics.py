from fastapi import APIRouter, Query, HTTPException
from app.db.mongo import db_helper 
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard(
    range: str = Query("all", description="Time filter range: today, 7days, 30days, all")
):
    db = getattr(db_helper, "db", None)
    
    if db is None:
        return {
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "status": "Database client not initialized"
        }
    match_filter = {}  
    now = datetime.utcnow()

    if range == "today":
        start_time = now - timedelta(days=1)
        match_filter["timestamp"] = {"$gte": start_time}
    elif range == "7days":
        start_time = now - timedelta(days=7)
        match_filter["timestamp"] = {"$gte": start_time}
    elif range == "30days":
        start_time = now - timedelta(days=30)
        match_filter["timestamp"] = {"$gte": start_time}
    elif range != "all":
        raise HTTPException(status_code=400, detail="Invalid range parameter ! Use 'today', '7days', '30days', ya 'all'.")
    

    pipeline = []
    if match_filter:
        pipeline.append({"$match": match_filter})
    
    pipeline.append({
        "$group": {
            "_id": None,
            "total_requests": {"$sum": 1},
            "total_tokens": {"$sum": "$tokens_used"},
            "total_cost": {"$sum": "$cost_usd"}
        }
    })
    
    try:
        cursor = db.logs.aggregate(pipeline)  
        result = await cursor.to_list(length=1)
        
        if not result:
            return {
                "range_filtered": range,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
            
        return {
            "range_filtered": range,
            "total_requests": result[0]["total_requests"],
            "total_tokens": result[0]["total_tokens"],
            "total_cost": round(result[0]["total_cost"], 8)
        }
    except Exception as e:
        return {
            "range_filtered": range,
            "total_requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "error": str(e)
        }