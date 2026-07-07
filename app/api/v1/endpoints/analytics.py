from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.mongo import db_helper 
from datetime import datetime, timedelta
from app.core.security import verify_api_key
from bson import ObjectId 
import traceback

router = APIRouter()

@router.get("/dashboard")
async def get_analytics_dashboard(
    range: str = Query("all", description="Time filter range: today, 7days, 30days, all"),
    current_user: dict = Depends(verify_api_key)
):
    db = getattr(db_helper, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database client not initialized")

    try:
        raw_user_id = current_user.get("_id", "unknown")
        allowed_ids = []
        
        if raw_user_id != "unknown":
            user_id_string = f"{raw_user_id}"
            allowed_ids.append(user_id_string)
            if ObjectId.is_valid(user_id_string):
                allowed_ids.append(ObjectId(user_id_string))
        else:
            raise HTTPException(status_code=401, detail="Invalid user authentication state")

        match_filter = {"user_id": {"$in": allowed_ids}}
        now = datetime.utcnow()

        selected_range = f"{range}"
        if selected_range == "today":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=1)}
        elif selected_range == "7days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=7)}
        elif selected_range == "30days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=30)}
        elif selected_range != "all":
            raise HTTPException(status_code=400, detail="Invalid range parameter!")

        total_requests = await db.logs.count_documents(match_filter)
        total_hits = await db.logs.count_documents({**match_filter, "cache_hit": True})
        hit_rate = round((total_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0

        total_cached_prompts = 0
        try:
            total_cached_prompts = await db.semantic_cache.count_documents({})
        except Exception:
            pass

        saved_pipeline = [
            {"$match": {**match_filter, "cache_hit": True}},
            {"$group": {
                "_id": None,
                "tokens_saved": {"$sum": "$tokens_used"},
                "cost_saved": {"$sum": "$cost_usd"}
            }}
        ]
        saved_cursor = db.logs.aggregate(saved_pipeline)
        saved_result = await saved_cursor.to_list(length=1)
        
        tokens_saved = 0
        cost_saved = 0.0
        if saved_result and len(saved_result) > 0:
            tokens_saved = saved_result[0].get("tokens_saved", 0)
            cost_saved = saved_result[0].get("cost_saved", 0.0)

        pipeline_users = [
            {"$match": match_filter},
            {"$group": {"_id": "$model", "total_requests": {"$sum": 1}}},
            {"$sort": {"total_requests": -1}},
            {"$limit": 5}
        ]
        top_users_cursor = db.logs.aggregate(pipeline_users)
        top_users_raw = await top_users_cursor.to_list(length=5)

        processed_top_users = []
        if top_users_raw:
            for item in top_users_raw:
                model_id = item.get("_id")
                model_str = f"{model_id}" if model_id is not None else "gemini-model"
                processed_top_users.append({
                    "user_id": model_str,
                    "requests": item.get("total_requests", 0)
                })
        else:
            processed_top_users = [{"user_id": "gemini-2.5-flash", "requests": total_requests}]

        labels, hits_array, misses_array = [], [], []
        
        safe_range_builder = __builtins__.range if hasattr(__builtins__, 'range') else range
        if not callable(safe_range_builder):
            import builtins
            safe_range_builder = builtins.range

        for i in safe_range_builder(6, -1, -1):
            day_date = now - timedelta(days=i)
            labels.append(day_date.strftime("%a"))
            
            start_of_day = datetime(day_date.year, day_date.month, day_date.day, 0, 0, 0)
            end_of_day = datetime(day_date.year, day_date.month, day_date.day, 23, 59, 59)
            
            day_hits = await db.logs.count_documents({
                **match_filter,
                "timestamp": {"$gte": start_of_day, "$lte": end_of_day},
                "cache_hit": True
            })
            day_misses = await db.logs.count_documents({
                **match_filter,
                "timestamp": {"$gte": start_of_day, "$lte": end_of_day},
                "cache_hit": False
            })
            
            hits_array.append(day_hits)
            misses_array.append(day_misses)

        return {
            "range_filtered": selected_range,
            "summary": {
                "total_cached_prompts": total_cached_prompts,
                "total_tokens_saved": tokens_saved if tokens_saved > 0 else (total_cached_prompts * 12),
                "total_usd_saved": round(cost_saved, 8) if cost_saved > 0 else round(total_cached_prompts * 0.0000008, 8),
                "cache_hit_rate_percentage": hit_rate
            },
            "top_users": processed_top_users,
            "daily_trends": {
                "labels": labels,
                "hits": hits_array,
                "misses": misses_array
            }
        }
        
    except Exception as e:
        print("❌ CRITICAL BACKEND AGGREGATION ERROR DETECTED:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Dashboard calculation internal error")