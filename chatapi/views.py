import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI

from .services import fetch_director_documents
from .tools import DOCUMENT_PICKER_TOOL
from .prompts import (
    FACTER_QUERY_ANALYZER_SYSTEM_PROMPT,
    FACTER_EXECUTION_AGENT_SYSTEM_PROMPT,
)

client = OpenAI()


@csrf_exempt
def chat_api(request):
    """
    Main chat endpoint for Facter Finance Assistant.
    Handles query analysis and document requests.
    """

    # AUTH
    if request.user is None:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method != "POST":
        return JsonResponse({"error": "Method Not Allowed"}, status=405)

    user_id = request.user.user_id

    # Parse body
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse(
            {"status": "error", "message": "Invalid JSON format"},
            status=400
        )

    user_message = data.get("message")
    org_id = data.get("org_id")
    dir_id = data.get("dir_id")

    if not user_message or not org_id or not dir_id:
        return JsonResponse(
            {"status": "error", "message": "message, org_id and dir_id are required"},
            status=400
        )

    # Agent 1 — Query analysis
    analyzer_response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": FACTER_QUERY_ANALYZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )

    try:
        analysis = json.loads(analyzer_response.choices[0].message.content)
    except Exception:
        return JsonResponse(
            {"status": "error", "message": "Failed to analyze user query"},
            status=500
        )

    question_type = analysis.get("question_type")
    explanation = analysis.get("explanation")

    if question_type == "GREETING":
        return JsonResponse({
            "status": "success",
            "reply": "Hi! I'm Facter Finance Assistant. I can help you with finance questions, tax and GST queries, compliance topics, and fetch your identity documents like Aadhaar, PAN, Voter ID, Passport, and Driving Licence. How can I assist you today?"
        })

    if question_type == "OUT_OF_SCOPE":
        return JsonResponse({
            "status": "success",
            "reply": "I can help only with finance and compliance-related questions."
        })

    documents = None

    # Fetch documents if needed
    if question_type in ["DOCUMENT_REQUEST", "DOCUMENT_LIST_REQUEST"]:
        try:
            documents = fetch_director_documents(
                request=request,
                org_id=org_id,
                dir_id=dir_id,
            )
            print(f"Documents received: {json.dumps(documents, indent=2)}")
        except Exception as e:
            if str(e) == "NO_ACCESS":
                no_access_response = client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are Facter Finance Assistant. The user asked for a document but they don't have access to it. Respond in a friendly, helpful way explaining this."
                        },
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.7,
                )
                return JsonResponse({
                    "status": "success",
                    "reply": no_access_response.choices[0].message.content,
                })
            return JsonResponse(
                {"status": "error", "message": str(e)},
                status=500
            )

    # Agent 2 — Execution
    executor_payload = {
        "question_type": question_type,
        "explanation": explanation,
        "original_question": user_message,
        "documents": documents,
    }

    executor_response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": FACTER_EXECUTION_AGENT_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(executor_payload)},
        ],
        tools=[DOCUMENT_PICKER_TOOL] if question_type == "DOCUMENT_REQUEST" else None,
        tool_choice="required" if question_type == "DOCUMENT_REQUEST" else None,
        temperature=0,
    )

    message = executor_response.choices[0].message

    if message.tool_calls:
        args = json.loads(message.tool_calls[0].function.arguments)
        return JsonResponse({
            "status": "success",
            "reply": args.get("reply_message"),
            "document_type": args.get("document_type"),
            "document_url": args.get("document_url"),
        })

    return JsonResponse({
        "status": "success",
        "reply": message.content,
    })
