from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.mongo import db_helper
from app.core.security import verify_api_key
from datetime import datetime, timedelta
from bson import ObjectId
import traceback

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    range: str = Query("all"),
    current_user: dict = Depends(verify_api_key)
):
    db = db_helper.db

    if db is None:
        raise HTTPException(500, "Database not initialized")

    try:
        # User ID
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(401, "Invalid user")

        match_filter = {
            "user_id": {
                "$in": [user_id, ObjectId(user_id)]
                if ObjectId.is_valid(str(user_id))
                else [user_id]
            }
        }

        # Time filter
        now = datetime.utcnow()

        if range == "today":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=1)}
        elif range == "7days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=7)}
        elif range == "30days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=30)}
        elif range != "all":
            raise HTTPException(400, "Invalid range")

        # Basic stats
        total_requests = await db.logs.count_documents(match_filter)
        total_hits = await db.logs.count_documents(
            {**match_filter, "cache_hit": True}
        )

        hit_rate = (
            round(total_hits * 100 / total_requests, 2)
            if total_requests
            else 0
        )

        # Cached prompts
        try:
            total_cached_prompts = await db.semantic_cache.count_documents({})
        except:
            total_cached_prompts = 0

        # Tokens & Cost saved
        pipeline = [
            {"$match": {**match_filter, "cache_hit": True}},
            {
                "$group": {
                    "_id": None,
                    "tokens_saved": {"$sum": "$tokens_used"},
                    "cost_saved": {"$sum": "$cost_usd"}
                }
            }
        ]

        result = await db.logs.aggregate(pipeline).to_list(1)

        tokens_saved = result[0]["tokens_saved"] if result else 0
        cost_saved = result[0]["cost_saved"] if result else 0

        # Top models
        pipeline = [
            {"$match": match_filter},
            {
                "$group": {
                    "_id": "$model",
                    "requests": {"$sum": 1}
                }
            },
            {"$sort": {"requests": -1}},
            {"$limit": 5}
        ]

        top_models = await db.logs.aggregate(pipeline).to_list(5)

        top_users = [
            {
                "user_id": item["_id"],
                "requests": item["requests"]
            }
            for item in top_models
        ]

        if not top_users:
            top_users = [{
                "user_id": "gemini-2.5-flash",
                "requests": total_requests
            }]

        # Daily Trends
        labels = []
        hits = []
        misses = []

        for i in range(6, -1, -1):
            day = now - timedelta(days=i)

            start = datetime(day.year, day.month, day.day)
            end = start + timedelta(days=1)

            labels.append(day.strftime("%a"))

            hits.append(
                await db.logs.count_documents({
                    **match_filter,
                    "timestamp": {
                        "$gte": start,
                        "$lt": end
                    },
                    "cache_hit": True
                })
            )

            misses.append(
                await db.logs.count_documents({
                    **match_filter,
                    "timestamp": {
                        "$gte": start,
                        "$lt": end
                    },
                    "cache_hit": False
                })
            )

        return {
            "range_filtered": range,
            "summary": {
                "total_cached_prompts": total_cached_prompts,
                "total_tokens_saved": tokens_saved,
                "total_usd_saved": round(cost_saved, 8),
                "cache_hit_rate_percentage": hit_rate
            },
            "top_users": top_users,
            "daily_trends": {
                "labels": labels,
                "hits": hits,
                "misses": misses
            }
        }

    except Exception:
        traceback.print_exc()
        raise HTTPException(500, "Dashboard error")