def translate_to_gemini_format(openai_body: dict) -> dict:
    openai_messages = openai_body.get("messages", [])
    gemini_contents = []
    system_instruction = None

    for msg in openai_messages:
        role = msg.get("role")
        content = msg.get("content")

        if role == "system":
            system_instruction = {"parts": [{"text": content}]}
        else:
            gemini_role = "model" if role == "assistant" else "user"
            gemini_contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

    gemini_payload = {"contents": gemini_contents}
    if system_instruction:
        gemini_payload["systemInstruction"] = system_instruction
    if "temperature" in openai_body and openai_body["temperature"] is not None:
        gemini_payload["generationConfig"] = {"temperature": openai_body["temperature"]}

    return gemini_payload
