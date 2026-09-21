import os
import json
from rich import print_json
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from dotenv import load_dotenv

_=load_dotenv()

EXCHANGE_RATES = { # 1 1 USD bằng bao nhiêu đơn vị tiền tệ này
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "VND": 25400.0,
}

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def calculate(expression: str) -> dict:
    return {"result": eval(expression)}

def convert_currency(amount: float, from_currency: str, to_currency:str) -> dict:
    # Chuan hoa
    from_currency = from_currency.strip().upper()
    to_currency = to_currency.strip().upper()
    amount = float(amount)

    if from_currency not in EXCHANGE_RATES or to_currency not in EXCHANGE_RATES:
        return {"error": f"Unsupported currency: {from_currency} to {to_currency}"}

    usd = amount / EXCHANGE_RATES[from_currency]
    target_amount = usd * EXCHANGE_RATES[to_currency]

    return {
        "original_amount": amount,
        "from_currency": from_currency,
        "to_currency": to_currency,
        "converted_amount": target_amount,
        "exchange_rate": round(EXCHANGE_RATES[to_currency]/EXCHANGE_RATES[from_currency], 4)
    }



TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression like '2+2*3'.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": "Convert currentcy, example 'convert 100USD to VND",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"}
                },
                "required":["amount", "from_currency", "to_currency"]
            }
        }
    }
]

messages: list[ChatCompletionMessageParam] = [
    {"role": "system", "content": "You are an Agent. Use tools when needed. When done, end your reply with FINAL ANSWER: <answer>."},
    {"role": "user", "content": "Convert $100 USD to EUR, then add 50."},
]

for i in range(10): #iteration cap = safety net, not the goal
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages= messages,
        tools= TOOLS
    )

    msg = resp.choices[0].message

    if not msg.tool_calls: # EXIT 1: model is done, text only
        print("FINAL: ", msg.content)
        break

    messages.append({
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {"id": tc.id, "type": "function", "function": {
                "name": tc.function.name,
                "arguments": tc.function.arguments
            }} for tc in msg.tool_calls if tc.type == "function"
        ]
    })

    for tc in msg.tool_calls: # EXECUTE each tool, append the observation
        if tc.type != "function":
            continue
        args = json.loads(tc.function.arguments)
        result = {}
        if tc.function.name == "calculate":
            result = calculate(**args)
        elif tc.function.name == "convert_currency":
            result = convert_currency(**args)
        else:
            result = {"error": f"tool: {tc.function.name}, id: {tc.id} is not available"}

        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result)
        })

    print("[iter]", i+1, "| messages: ", len(messages), "| roles:", [m['role'] for m in messages])


