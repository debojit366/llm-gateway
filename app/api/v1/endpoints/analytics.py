from fastapi import APIRouter, Query, HTTPException, Depends
from app.db.mongo import db_helper
from app.core.security import verify_api_key
from app.db.qdrant_client import qdrant_client, COLLECTION_NAME
from datetime import datetime, timedelta, time
from bson import ObjectId
import traceback
import asyncio

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(
    range_param: str = Query("all"),
    current_user: dict = Depends(verify_api_key)
):
    db = db_helper.db
    if db is None:
        raise HTTPException(500, "Database not initialized")

    try:
        user_id = current_user.get("_id")
        if not user_id:
            raise HTTPException(401, "Invalid user")

        # Clean & robust User ID matching (Supports String + ObjectId)
        str_user_id = str(user_id)
        user_ids_to_match = [str_user_id]
        if ObjectId.is_valid(str_user_id):
            user_ids_to_match.append(ObjectId(str_user_id))

        match_filter = {"user_id": {"$in": user_ids_to_match}}

        # Time filter
        now = datetime.utcnow()
        if range_param == "today":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=1)}
        elif range_param == "7days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=7)}
        elif range_param == "30days":
            match_filter["timestamp"] = {"$gte": now - timedelta(days=30)}
        elif range_param != "all":
            raise HTTPException(400, "Invalid range parameter")

        # Basic Stats
        total_requests = await db.logs.count_documents(match_filter)
        total_hits = await db.logs.count_documents({**match_filter, "cache_hit": True})
        hit_rate = round((total_hits * 100 / total_requests), 2) if total_requests else 0.0

        # Total cached prompts count directly from Qdrant
        try:
            loop = asyncio.get_running_loop()
            qdrant_info = await loop.run_in_executor(
                None, lambda: qdrant_client.get_collection(COLLECTION_NAME)
            )
            total_cached_prompts = qdrant_info.points_count
        except Exception:
            total_cached_prompts = 0

        # Tokens & Cost saved
        savings_pipeline = [
            {"$match": {**match_filter, "cache_hit": True}},
            {
                "$group": {
                    "_id": None,
                    "tokens_saved": {"$sum": "$tokens_used"},
                    "cost_saved": {"$sum": "$cost_usd"}
                }
            }
        ]
        savings_res = await db.logs.aggregate(savings_pipeline).to_list(1)
        tokens_saved = savings_res[0]["tokens_saved"] if savings_res else 0
        cost_saved = round(savings_res[0]["cost_saved"], 8) if savings_res else 0.0

        # ------------------ ⚡ TOP MODELS / MODEL DISTRIBUTION FIX ------------------
        top_models_pipeline = [
            {"$match": match_filter},
            {
                "$project": {
                    # Strip "-cached" suffix from model names so they group together
                    "clean_model": {
                        "$replaceAll": {
                            "input": {"$ifNull": ["$model", "unknown"]},
                            "find": "-cached",
                            "replacement": ""
                        }
                    }
                }
            },
            {"$group": {"_id": "$clean_model", "requests": {"$sum": 1}}},
            {"$sort": {"requests": -1}},
            {"$limit": 5}
        ]
        models_res = await db.logs.aggregate(top_models_pipeline).to_list(5)

        top_models = [
            {
                "model": item["_id"],
                "name": item["_id"],        # Recharts / Donut chart label compatibility
                "requests": item["requests"],
                "value": item["requests"]    # Recharts value compatibility
            }
            for item in models_res
        ]

        # Complete fallback object if no models are logged yet
        if not top_models:
            top_models = [{
                "model": "gemini-2.5-flash",
                "name": "gemini-2.5-flash",
                "requests": total_requests,
                "value": total_requests
            }]
        # -------------------------------------------------------------------------

        # Daily Trends (Last 7 Days)
        seven_days_ago = datetime.combine(now.date() - timedelta(days=6), time.min)
        trends_pipeline = [
            {
                "$match": {
                    **match_filter,
                    "timestamp": {"$gte": seven_days_ago}
                }
            },
            {
                "$group": {
                    "_id": {
                        "day": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                        "hit": "$cache_hit"
                    },
                    "count": {"$sum": 1}
                }
            }
        ]
        trends_raw = await db.logs.aggregate(trends_pipeline).to_list(None)

        # Mapping pipeline data into structured response
        trends_map = {}
        for i in range(6, -1, -1):
            day_dt = now - timedelta(days=i)
            day_str = day_dt.strftime("%Y-%m-%d")
            label_str = day_dt.strftime("%a")
            trends_map[day_str] = {"label": label_str, "hits": 0, "misses": 0}

        for item in trends_raw:
            day_key = item["_id"]["day"]
            if day_key in trends_map:
                if item["_id"]["hit"]:
                    trends_map[day_key]["hits"] = item["count"]
                else:
                    trends_map[day_key]["misses"] = item["count"]

        labels = [v["label"] for v in trends_map.values()]
        hits = [v["hits"] for v in trends_map.values()]
        misses = [v["misses"] for v in trends_map.values()]

        return {
            "range_filtered": range_param,
            "summary": {
                "total_cached_prompts": total_cached_prompts,
                "total_tokens_saved": tokens_saved,
                "total_usd_saved": cost_saved,
                "cache_hit_rate_percentage": hit_rate
            },
            "top_models": top_models,
            "model_distribution": top_models,  # Added for Frontend chart compatibility
            "daily_trends": {
                "labels": labels,
                "hits": hits,
                "misses": misses
            }
        }

    except Exception:
        traceback.print_exc()
        raise HTTPException(500, "Dashboard error")