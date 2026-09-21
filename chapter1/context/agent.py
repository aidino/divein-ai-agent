import os
import json
from rich import print_json
from enum import Enum
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

class EXP_MODE(Enum):
    FULL = 0
    NO_HISTORY = 1
    NO_TOOLS_CALL = 2
    NO_TOOLS_RESULT = 3
    NO_REASONING = 4

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")

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


def filter_messages(messages: list[ChatCompletionMessageParam], mode: EXP_MODE) -> list[ChatCompletionMessageParam]:
    """Ablation filter: cắt bỏ thành phần context theo mode trước khi gửi LLM."""
    if mode == EXP_MODE.FULL:
        return messages

    if mode == EXP_MODE.NO_HISTORY:
        return messages[:2]  # chỉ system + user gốc

    # NO_REASONING: strip reasoning_content khỏi assistant
    if mode == EXP_MODE.NO_REASONING:
        return [
            {k: v for k, v in m.items() if k != "reasoning_content"}  # type: ignore[union-attr]
            if m.get("role") == "assistant" and "reasoning_content" in m  # type: ignore[union-attr, operator]
            else m
            for m in messages
        ]

    return messages  # FULL, NO_TOOLS_CALL, NO_TOOLS_RESULT → không filter messages


def do_experiment(mode: EXP_MODE):
    print(f"\n{'='*60}")
    print(f"  ABLATION EXPERIMENT: {mode.name}")
    print(f"{'='*60}\n")

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": "You are an Agent. Use tools when needed. When done, end your reply with FINAL ANSWER: <answer>."},
        {"role": "user", "content": "Convert $100 USD to EUR, then add 50."},
    ]

    for i in range(10): #iteration cap = safety net, not the goal
        # Ablation: filter messages trước khi gửi LLM
        llm_messages = filter_messages(messages, mode)

        print(f"  [iter {i+1}] full_history={len(messages)} → sent_to_llm={len(llm_messages)} | roles: {[m.get('role') for m in llm_messages]}") # type: ignore[union-attr]

        # NO_TOOLS_CALL: không gửi tools → model không thể gọi tool
        tools = None if mode == EXP_MODE.NO_TOOLS_CALL else TOOLS

        resp = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages= llm_messages,
            tools= tools, # type: ignore
            extra_body={"thinking": {"type": "enabled"}} # "low" | "medium" | "high" — mặc định "medium"
        )
        # print("============ RESPONSE LOG for DEBUGGING ================")
        # print_json(resp.model_dump_json())
        # print("============ END =========================")
        msg = resp.choices[0].message

        if not msg.tool_calls: # EXIT 1: model is done, text only
            if msg.reasoning_content: # type: ignore[attr-defined]
                print("  Thinking: ", msg.reasoning_content) # type: ignore[attr-defined]
            print("  FINAL: ", msg.content)
            break

        # Luôn append vào messages GỐC (full history) — không bao giờ mất data
        assistant_msg: dict = {
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {"id": tc.id, "type": "function", "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }} for tc in msg.tool_calls if tc.type == "function"
            ]
        }
        # Lưu reasoning_content nếu có (để NO_REASONING mode có thể filter)
        if hasattr(msg, 'reasoning_content') and msg.reasoning_content: # type: ignore[attr-defined]
            assistant_msg["reasoning_content"] = msg.reasoning_content # type: ignore[attr-defined]
        messages.append(assistant_msg) # type: ignore

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
                # NO_TOOLS_RESULT: giữ tool message nhưng content rỗng → model "mù"
                "content": "" if mode == EXP_MODE.NO_TOOLS_RESULT else json.dumps(result)
            })

    print(f"\n  [DONE] {mode.name} — total messages in full history: {len(messages)}\n")


# ── Chạy tất cả ablation experiments ──
if __name__ == "__main__":
    for mode in EXP_MODE:
        do_experiment(mode=mode)
