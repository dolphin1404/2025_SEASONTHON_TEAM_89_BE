import re
import json
import httpx
import asyncio

from .check_fraud_queue import CheckFraudQueue
from .check_fraud_result_dict import CheckFraudResultDict
from app.schemas.check_fraud import LLMResponse

from app import OLLAMA_URL, OLLAMA_MODEL

find_res = re.compile(r'({\n?\s*"risk_level":\s?"(정상|주의|위험)",\n?\s*"confidence":\s?((\d|\.)+),\n?\s+"detected_patterns":\s?(\[.*\]),\n?\s*"explanation":\s?"(.*)",\n?\s*"recommended_action":\s?"(.*)"\n?})')

async def request_ollama(original_text: str):
    async with httpx.AsyncClient() as client:
        prompt = f"""You are "위허메," an AI expert specializing in detecting financial fraud, investment scams, and phishing within Korean messaging conversations. Your purpose is to analyze conversational context and identify genuine patterns of manipulation and deception. Be accurate and balanced - do not over-classify normal conversations as suspicious.

CRITICAL: Analyze ONLY the message provided in the ANALYSIS SECTION below. Do NOT confuse it with the examples.

Your output MUST be a single, valid JSON object and nothing else. Do not include any explanatory text, code blocks, or markdown formatting before or after the JSON.

IMPORTANT GUIDELINES:
Normal daily conversations (games, casual chat, greetings, food questions) should be marked as "정상" with high confidence
Only mark as "주의" or "위험" when there are clear fraud indicators
Consider context and common sense - not every mention of money or urgency is a scam
Be precise with confidence scores based on actual evidence

The JSON object must conform to the following schema:
{{
  "risk_level": "string", // Must be one of: "정상", "주의", "위험"
  "confidence": "float", // A value between 0.0 and 1.0 indicating the confidence of the risk_level assessment.
  "detected_patterns": "array[string]", // A list of detected scam patterns. Examples: "과도한 수익 보장", "긴급한 입금 요구", "개인정보 요구", "비공개 정보 언급", "의심스러운 링크"
  "explanation": "string", // A brief, clear explanation in Korean for the user (max 50 characters).
  "recommended_action": "string" // Must be one of: "전송 전 확인", "전송 중단 권고", "없음"
}}
===== TRAINING EXAMPLES (DO NOT ANALYZE THESE) =====

Example A - ACTUAL SCAM (위험):
Input: "급하게 돈 보낼 데가 있는데 150만원만 OOO(01-234-567) 계좌로 보내줘"
Output: {{"risk_level": "위험", "confidence": 0.95, "detected_patterns": ["긴급한 입금 요구"], "explanation": "계좌이체 요구는 사기일 가능성이 높습니다.", "recommended_action": "전송 중단 권고"}}

Example B - NORMAL FOOD QUESTION (정상):
Input: "내일 학식 뭐야?"
Output: {{"risk_level": "정상", "confidence": 0.99, "detected_patterns": [], "explanation": "학교 급식에 대한 일상적인 질문입니다.", "recommended_action": "없음"}}

Example C - NORMAL GAME (정상):
Input: "롤이나 하자"
Output: {{"risk_level": "정상", "confidence": 0.99, "detected_patterns": [], "explanation": "게임 제안으로 정상적인 대화입니다.", "recommended_action": "없음"}}

Example D - INVESTMENT SCAM (위험):
Input: "원금 보장에 수익률 300% 보장합니다"
Output: {{"risk_level": "위험", "confidence": 0.98, "detected_patterns": ["과도한 수익 보장"], "explanation": "비현실적인 수익률 제안은 사기일 가능성이 높습니다.", "recommended_action": "전송 중단 권고"}}

===== END OF EXAMPLES =====

===== ACTUAL ANALYSIS TASK =====

IMPORTANT: Analyze ONLY this message below. Ignore all examples above.

Current Message to Analyze:
"{original_text}"

Analyze the above message and provide accurate JSON output based on its actual content.
"""
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }

        response = await client.post(f"{OLLAMA_URL}/api/generate", json=data)
        return response.json()['response']

async def process_queue(cfq: CheckFraudQueue, cfrd: CheckFraudResultDict):
    while True:
        original_text = cfq.pop()
        if original_text is not None:
            try:
                status = "failed"
                res = None
                result_LLMResponse = None
                for _ in range(3):  # Retry up to 3 times
                    result = await request_ollama(original_text)
                    res = find_res.findall(result)

                    if res:
                        status = "success"
                        break
                    await asyncio.sleep(1)
                
                if status == "success":
                    result_dict = json.loads(res[0][0])
                    result_LLMResponse = LLMResponse(**result_dict)
                else:
                    result_LLMResponse = False

                cfrd.insert(original_text, result_LLMResponse)
            except Exception as e:
                print(f"[ERROR] 큐 처리 중 오류 발생: {e}")
                # handle error (e.g., log or requeue)
                pass
        else:
            await asyncio.sleep(1)  # wait before checking again

async def start_processing():
    """백그라운드 큐 처리 태스크 시작"""
    task = asyncio.create_task(process_queue(CheckFraudQueue(), CheckFraudResultDict()))
    return task