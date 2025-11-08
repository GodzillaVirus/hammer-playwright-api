from fastapi import FastAPI
import requests
import json
from typing import Optional, Dict, Any
import asyncio

BASE_HEADERS = {
    'authority': 'gemini.browserbase.com',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'no-cache',
    'origin': 'https://gemini.browserbase.com',
    'pragma': 'no-cache',
    'referer': 'https://gemini.browserbase.com/',
    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
}

ai_sessions: Dict[str, str] = {}

async def create_ai_session() -> Optional[str]:
    session_url = 'https://gemini.browserbase.com/api/session'
    
    session_headers = BASE_HEADERS.copy()
    session_headers['accept'] = '*/*'
    session_headers['content-type'] = 'application/json'

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(session_url, headers=session_headers, json={'timezone': 'EEST'})
        )
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data.get('sessionId')
        
        if session_id:
            return session_id
        return None
    except Exception as e:
        print(f"AI Session Error: {e}")
        return None

async def execute_ai_command(session_id: str, prompt: str) -> Dict[str, Any]:
    stream_headers = BASE_HEADERS.copy()
    stream_headers['accept'] = 'text/event-stream'
    params = {'sessionId': session_id, 'goal': prompt}
    
    result = {
        "success": False,
        "thoughts": [],
        "final_message": "",
        "summary": ""
    }

    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.get(
                'https://gemini.browserbase.com/api/agent/stream',
                params=params,
                headers=stream_headers,
                stream=True,
                timeout=300
            )
        )
        response.raise_for_status()

        summary_text = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data:'):
                    json_data_str = decoded_line[5:].strip()
                    try:
                        data = json.loads(json_data_str)
                        
                        if data.get('category') == 'agent':
                            level = data.get('level')
                            message = data.get('message')
                            if level == 1 and message and '💭' in message:
                                clean_message = message.replace('💭', '').strip()
                                result["thoughts"].append(clean_message)
                        
                        if data.get('success') is True:
                            result["success"] = True
                            result["final_message"] = data.get('finalMessage', '')
                        
                        if 'token' in data:
                            summary_text += data['token']
                            
                    except json.JSONDecodeError:
                        continue
        
        result["summary"] = summary_text
        return result
        
    except Exception as e:
        result["error"] = str(e)
        return result
