from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.mongo import db_helper 
from datetime import datetime, timedelta
from app.core.security import verify_api_key
from bson import ObjectId 

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard(
    range: str = Query("all", description="Time filter range: today, 7days, 30days, all"),
    current_user: dict = Depends(verify_api_key)
):
    db = getattr(db_helper, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database client not initialized")

    user_id = current_user["_id"]
    
    allowed_ids = [str(user_id)]
    if ObjectId.is_valid(str(user_id)):
        allowed_ids.append(ObjectId(str(user_id)))

    match_filter = {"user_id": {"$in": allowed_ids}}
    
    now = datetime.utcnow()

    if range == "today":
        match_filter["timestamp"] = {"$gte": now - timedelta(days=1)}
    elif range == "7days":
        match_filter["timestamp"] = {"$gte": now - timedelta(days=7)}
    elif range == "30days":
        match_filter["timestamp"] = {"$gte": now - timedelta(days=30)}
    elif range != "all":
        raise HTTPException(status_code=400, detail="Invalid range parameter bhai!")

    pipeline = [
        {"$match": match_filter},
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
        raise HTTPException(status_code=500, detail=f"Aggregation error: {str(e)}")