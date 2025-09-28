"""
AI Content Analyzer for FlushBot
Integrates with OpenRouter API (Grok-4 and Gemini 2.0) for intelligent content analysis
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import httpx
from loguru import logger

from config.settings import settings
from config.security_rules import security_rules, is_exempt_content


class APIQuotaManager:
    """Manages AI API quota and rate limiting"""
    
    def __init__(self):
        self.daily_usage = 0
        self.hourly_usage = 0
        self.last_reset = datetime.now()
        self.last_hourly_reset = datetime.now()
        self.request_times = []
    
    def can_make_request(self) -> bool:
        """Check if we can make an API request within quota limits"""
        now = datetime.now()
        
        # Reset daily quota
        if now.date() != self.last_reset.date():
            self.daily_usage = 0
            self.last_reset = now
        
        # Reset hourly quota
        if now - self.last_hourly_reset >= timedelta(hours=1):
            self.hourly_usage = 0
            self.last_hourly_reset = now
        
        # Clean old request times (last minute)
        minute_ago = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > minute_ago]
        
        # Check all limits
        if self.daily_usage >= settings.daily_api_quota:
            logger.warning("Daily API quota exceeded")
            return False
        
        if self.hourly_usage >= settings.hourly_api_quota:
            logger.warning("Hourly API quota exceeded")
            return False
        
        if len(self.request_times) >= settings.api_rate_limit:
            logger.warning("Rate limit exceeded")
            return False
        
        return True
    
    def record_request(self):
        """Record an API request"""
        now = datetime.now()
        self.daily_usage += 1
        self.hourly_usage += 1
        self.request_times.append(now)
    
    def get_quota_status(self) -> Dict:
        """Get current quota status"""
        return {
            "daily_used": self.daily_usage,
            "daily_limit": settings.daily_api_quota,
            "hourly_used": self.hourly_usage,
            "hourly_limit": settings.hourly_api_quota,
            "rate_limit_used": len(self.request_times),
            "rate_limit": settings.api_rate_limit
        }


class AIContentAnalyzer:
    """AI-powered content analyzer using OpenRouter API"""
    
    def __init__(self):
        self.quota_manager = APIQuotaManager()
        self.client = httpx.AsyncClient(timeout=settings.request_timeout)
        self.fallback_active = False
    
    async def analyze_content(self, text: str, context: Optional[Dict] = None) -> Dict:
        """
        Analyze content for policy violations using AI
        
        Args:
            text: Message text to analyze
            context: Additional context (user info, chat info, etc.)
            
        Returns:
            Analysis result with violations, confidence, and recommendations
        """
        # 🔍 DETAILED AI ANALYSIS LOGGING
        logger.info(f"🤖 AI ANALYSIS START | Text: '{text[:100]}...' | Length: {len(text)}")
        
        # Check for exempt content first
        if is_exempt_content(text):
            logger.info(f"⚪ EXEMPT CONTENT | Skipping analysis")
            return {
                "violations": [],
                "confidence": 0.0,
                "action": "allow",
                "reason": "exempt_content",
                "ai_analysis": False
            }
        
        # Run rule-based analysis with multi-message context
        user_id = context.get("user_id") if context else None
        timestamp = context.get("timestamp") if context else None
        
        rule_violations = security_rules.analyze_message(text, user_id=user_id, timestamp=timestamp)
        logger.info(f"📋 RULE ANALYSIS | Found {len(rule_violations)} violations: {[v['category'] for v in rule_violations]}")
        
        # If we have high-confidence rule violations, may not need AI
        high_confidence_violations = [v for v in rule_violations if v["confidence"] > 0.8]
        
        if high_confidence_violations and not settings.mock_ai_responses:
            logger.info(f"🎯 HIGH CONFIDENCE RULES | Skipping AI analysis - Categories: {[v['category'] for v in high_confidence_violations]}")
            return {
                "violations": rule_violations,
                "confidence": max(v["confidence"] for v in rule_violations),
                "action": "restrict",
                "reason": "high_confidence_rule_match",
                "ai_analysis": False
            }
        
        # MINIMIZE API USAGE - Only use AI for truly uncertain cases
        # If we have ANY rule violations, trust the comprehensive database
        if rule_violations:
            logger.info(f"📋 RULE-BASED DECISION | Found {len(rule_violations)} violations, skipping AI to save quota")
            return {
                "violations": rule_violations,
                "confidence": max(v["confidence"] for v in rule_violations),
                "action": "restrict" if rule_violations else "allow",
                "reason": "comprehensive_rule_match",
                "ai_analysis": False
            }
        
        # Only use AI if NO rule violations found AND quota available
        if self.quota_manager.can_make_request() and not rule_violations:
            logger.info(f"🧠 AI ANALYSIS | No rule violations found, checking with AI for edge cases")
            ai_result = await self._ai_analyze(text, context, rule_violations)
            return ai_result
        else:
            # No violations found and no AI needed
            logger.info(f"✅ CLEAN MESSAGE | No rule violations, no AI needed")
            return {
                "violations": rule_violations,
                "confidence": max([v["confidence"] for v in rule_violations], default=0.0),
                "action": "warn" if rule_violations else "allow",
                "reason": "quota_exceeded_fallback",
                "ai_analysis": False
            }
    
    async def _ai_analyze(self, text: str, context: Optional[Dict], rule_violations: List[Dict]) -> Dict:
        """Perform AI analysis using OpenRouter API"""
        
        if settings.mock_ai_responses:
            return self._mock_ai_response(text, rule_violations)
        
        # Prepare AI prompt
        prompt = self._build_analysis_prompt(text, context, rule_violations)
        
        # Try primary API (Grok-4) first
        try:
            result = await self._call_openrouter_api(prompt, use_fallback=False)
            if result:
                return result
        except Exception as e:
            logger.error(f"Primary AI API failed: {e}")
        
        # Try fallback API (Gemini 2.0)
        try:
            logger.info("Using fallback AI API (Gemini 2.0)")
            self.fallback_active = True
            result = await self._call_openrouter_api(prompt, use_fallback=True)
            if result:
                return result
        except Exception as e:
            logger.error(f"Fallback AI API failed: {e}")
        
        # If both APIs fail, use rule-based analysis
        return {
            "violations": rule_violations,
            "confidence": max([v["confidence"] for v in rule_violations], default=0.0),
            "action": "warn" if rule_violations else "allow", 
            "reason": "ai_api_failed",
            "ai_analysis": False
        }
    
    def _build_analysis_prompt(self, text: str, context: Optional[Dict], rule_violations: List[Dict]) -> str:
        """Build AI analysis prompt"""
        prompt = f"""
        You are a content moderation AI for a Telegram security bot. Analyze the following message for policy violations.

        MESSAGE: "{text}"

        CONTEXT: {json.dumps(context or {}, indent=2)}

        EXISTING RULE VIOLATIONS: {json.dumps(rule_violations, indent=2)}

        POLICIES TO CHECK:
        1. Illegal drug sales/distribution
        2. Child exploitation/abuse content (CP)
        3. Weapons sales/trafficking
        4. Hate speech/terrorism
        5. Fraud/scams
        6. Spam/unwanted advertising

        SECURITY LEVELS:
        - LOW: Warning only
        - MEDIUM: Progressive restrictions  
        - EXTREME: Immediate ban for violations

        Respond in JSON format:
        {{
            "violations": [
                {{
                    "category": "category_name",
                    "severity": "low|medium|high|critical", 
                    "confidence": 0.0-1.0,
                    "explanation": "why this is a violation"
                }}
            ],
            "overall_confidence": 0.0-1.0,
            "recommended_action": "allow|warn|restrict|ban",
            "reasoning": "explanation of decision",
            "false_positive_risk": 0.0-1.0
        }}
        """
        return prompt
    
    async def _call_openrouter_api(self, prompt: str, use_fallback: bool = False) -> Optional[Dict]:
        """Call OpenRouter API with specified model"""
        
        headers = settings.get_ai_headers(use_fallback)
        model = settings.get_ai_model(use_fallback)
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert content moderation AI. Respond only in valid JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            self.quota_manager.record_request()
            
            response = await self.client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Parse AI response
                try:
                    ai_result = json.loads(content)
                    return self._process_ai_response(ai_result)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON response from AI API")
                    return None
            else:
                logger.error(f"AI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"AI API request failed: {e}")
            return None
    
    def _process_ai_response(self, ai_result: Dict) -> Dict:
        """Process and validate AI response"""
        return {
            "violations": ai_result.get("violations", []),
            "confidence": ai_result.get("overall_confidence", 0.0),
            "action": ai_result.get("recommended_action", "allow"),
            "reason": ai_result.get("reasoning", "ai_analysis"),
            "ai_analysis": True,
            "false_positive_risk": ai_result.get("false_positive_risk", 0.0)
        }
    
    def _mock_ai_response(self, text: str, rule_violations: List[Dict]) -> Dict:
        """Mock AI response for testing"""
        # Simple mock based on rule violations
        if rule_violations:
            max_confidence = max(v["confidence"] for v in rule_violations)
            return {
                "violations": rule_violations,
                "confidence": min(max_confidence + 0.2, 1.0),
                "action": "warn" if max_confidence < 0.7 else "restrict",
                "reason": "mock_ai_analysis",
                "ai_analysis": True,
                "false_positive_risk": 0.1
            }
        else:
            return {
                "violations": [],
                "confidence": 0.0,
                "action": "allow",
                "reason": "mock_ai_clean",
                "ai_analysis": True,
                "false_positive_risk": 0.0
            }
    
    async def batch_analyze(self, messages: List[Dict]) -> List[Dict]:
        """
        Analyze multiple messages in batch for efficiency
        
        Args:
            messages: List of message dicts with 'text' and optional 'context'
            
        Returns:
            List of analysis results
        """
        results = []
        
        # Process in chunks to respect rate limits
        chunk_size = min(settings.batch_processing_size, len(messages))
        
        for i in range(0, len(messages), chunk_size):
            chunk = messages[i:i + chunk_size]
            
            # Analyze chunk concurrently
            tasks = [
                self.analyze_content(msg.get("text", ""), msg.get("context"))
                for msg in chunk
            ]
            
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.error(f"Batch analysis failed for message {i+j}: {result}")
                    results.append({
                        "violations": [],
                        "confidence": 0.0,
                        "action": "allow",
                        "reason": "batch_analysis_failed",
                        "ai_analysis": False
                    })
                else:
                    results.append(result)
            
            # Rate limiting between chunks
            if i + chunk_size < len(messages):
                await asyncio.sleep(1)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get analyzer statistics"""
        return {
            "quota_status": self.quota_manager.get_quota_status(),
            "fallback_active": self.fallback_active,
            "api_available": self.quota_manager.can_make_request()
        }
    
    async def _create_mock_result(self, message_data: Dict) -> Dict:
        """Create mock analysis result for testing"""
        return {
            "analysis": {
                "violations": [],
                "severity": "none",
                "confidence": 0.0,
                "recommendations": []
            },
            "ai_provider": "mock",
            "processing_time": 0.1,
            "quota_used": False
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global analyzer instance
ai_analyzer = AIContentAnalyzer()