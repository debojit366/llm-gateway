import json
import time
def create_openai_chunk(chunk_id: str, model_name: str, text: str, finish_reason: str = None) -> str:
    chunk_data = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model_name,
        "choices": [
            {
                "index": 0,
                "delta": {"content": text} if text else {},
                "finish_reason": finish_reason
            }
        ]
    }
    return f"data: {json.dumps(chunk_data)}\n\n"
