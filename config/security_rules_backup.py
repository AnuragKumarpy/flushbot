"""
Security Rules and Policies for FlushBot
Defines content detection patterns, violation categories, and enforcement rules
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum
from dataclasses import dataclass
                    # Direct weapon selling
                    r"\b(selling|buying|trading|dealing)\s*(guns?|weapons?|firearms?|ammunition|ammo)",
                    r"\b(pistol|rifle|shotgun|ak47|ar15|glock|bullets?|grenades?)\s*(for\s*sale|selling|available)",
                    r"\b(gun\s*dealer|arms\s*dealer|weapons?\s*supplier)",
                    r"\b(explosives?|bombs?|c4|dynamite)\s*(selling|available|for\s*sale)",
                    # Bypass patterns
                    *WEAPONS_BYPASS_PATTERNS,
                    # Combined bypass - selling + weapons
                    r"(?=.*s[\s\.\-_]*e[\s\.\-_]*l[\s\.\-_]*l)(?=.*g[\s\.\-_]*u[\s\.\-_]*n)",  # sell + gun
                    r"(?=.*b[\s\.\-_]*u[\s\.\-_]*y)(?=.*w[\s\.\-_]*e[\s\.\-_]*a[\s\.\-_]*p)",  # buy + weapon
                    # Multi-language
                    r"\b(बेचना|खरीदना)\s*(बंदूक|हथियार)",
                    r"\b(продаю|покупаю)\s*(оружие|пистолет|автомат)",
                    r"\b(vendiendo|comprando)\s*(armas|pistola|fusil)",
                ],
                bypass_patterns=WEAPONS_BYPASS_PATTERNS + SELLING_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Weapon/firearm selling - TOS violation"
            ),
            
            # SCAM/FRAUD - DELETE IN MEDIUM/EXTREME
            "scam_fraud": ViolationRule(
                category="scam_fraud",
                patterns=[
                    # Direct scam patterns
                    r"\b(credit\s*card\s*fraud|carding|money\s*laundering|counterfeit)",
                    r"\b(fake\s*ids?|stolen\s*cards?|cloned\s*cards?)",
                    r"\b(phishing\s*kit|scam\s*method|fraud\s*tutorial)",
                    r"\b(paypal\s*hack|bank\s*hack|crypto\s*scam)",
                    # Bypass patterns
                    *SCAM_BYPASS_PATTERNS,
                    # Multi-language
                    r"\b(जालसाजी|धोखाधड़ी|फर्जी)",
                    r"\b(мошенничество|обман|фальшивка)",
                    r"\b(estafa|fraude|tarjetas\s*clonadas)",
                ],
                bypass_patterns=SCAM_BYPASS_PATTERNS,
                severity=ViolationSeverity.HIGH,
                description="Scam/fraud activities - TOS violation"
            ),
            
            # TELEGRAM TOS VIOLATIONS - DELETE IN MEDIUM/EXTREME
            "telegram_violations": ViolationRule(ptional
from enum import Enum
from dataclasses import dataclass

class ViolationSeverity(Enum):
    """Violation severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class SecurityMode(Enum):
    """Security enforcement modes"""
    LOW = "low"          # Only serious violations: CP, drugs selling, weapons, child abuse - protect from Telegram bans
    MEDIUM = "medium"    # All drug references, CP, weapons, scams, ToS violations (any language)
    EXTREME = "extreme"  # Everything from medium + abusive material, but NO BANS - only silent deletions

@dataclass
class ViolationRule:
    """Represents a content violation rule"""
    category: str
    patterns: List[str]
    severity: ViolationSeverity
    description: str
    confidence: float = 0.8
    languages: List[str] = None
    bypass_patterns: List[str] = None  # Common bypass attempts

# Comprehensive TOS Violations Database - Protect Groups from Telegram Bans
# Patterns designed to catch bypass attempts and multi-message splitting

# Drug-related bypass patterns for split messages
DRUG_BYPASS_PATTERNS = [
    r'd[\s\.\-_]*r[\s\.\-_]*u[\s\.\-_]*g[\s\.\-_]*s?',  # d r u g s
    r'w[\s\.\-_]*e[\s\.\-_]*e[\s\.\-_]*d',  # w e e d  
    r'c[\s\.\-_]*o[\s\.\-_]*k[\s\.\-_]*e',  # c o k e
    r'm[\s\.\-_]*e[\s\.\-_]*t[\s\.\-_]*h',  # m e t h
    r'h[\s\.\-_]*e[\s\.\-_]*r[\s\.\-_]*o[\s\.\-_]*i[\s\.\-_]*n',  # h e r o i n
    r'g[\s\.\-_]*a[\s\.\-_]*n[\s\.\-_]*j[\s\.\-_]*a',  # g a n j a
    r'm[\s\.\-_]*d[\s\.\-_]*m[\s\.\-_]*a',  # m d m a
    r'l[\s\.\-_]*s[\s\.\-_]*d',  # l s d
    r'x[\s\.\-_]*t[\s\.\-_]*c',  # x t c / ecstasy
    r'o[\s\.\-_]*p[\s\.\-_]*i[\s\.\-_]*u[\s\.\-_]*m',  # o p i u m
    r'c[\s\.\-_]*r[\s\.\-_]*a[\s\.\-_]*c[\s\.\-_]*k',  # c r a c k
    r'h[\s\.\-_]*a[\s\.\-_]*s[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*s[\s\.\-_]*h',  # h a s h i s h
]

# Selling/Trading bypass patterns
SELLING_BYPASS_PATTERNS = [
    r's[\s\.\-_]*e[\s\.\-_]*l[\s\.\-_]*l[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # s e l l i n g
    r'f[\s\.\-_]*o[\s\.\-_]*r[\s\.\-_]*s[\s\.\-_]*a[\s\.\-_]*l[\s\.\-_]*e',  # f o r s a l e
    r'b[\s\.\-_]*u[\s\.\-_]*y[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # b u y i n g
    r't[\s\.\-_]*r[\s\.\-_]*a[\s\.\-_]*d[\s\.\-_]*e',  # t r a d e
    r'a[\s\.\-_]*v[\s\.\-_]*a[\s\.\-_]*i[\s\.\-_]*l[\s\.\-_]*a[\s\.\-_]*b[\s\.\-_]*l[\s\.\-_]*e',  # a v a i l a b l e
    r'w[\s\.\-_]*a[\s\.\-_]*n[\s\.\-_]*t[\s\.\-_]*e[\s\.\-_]*d',  # w a n t e d
]

# Weapons bypass patterns  
WEAPONS_BYPASS_PATTERNS = [
    r'g[\s\.\-_]*u[\s\.\-_]*n[\s\.\-_]*s?',  # g u n s
    r'w[\s\.\-_]*e[\s\.\-_]*a[\s\.\-_]*p[\s\.\-_]*o[\s\.\-_]*n[\s\.\-_]*s?',  # w e a p o n s
    r'a[\s\.\-_]*m[\s\.\-_]*m[\s\.\-_]*o',  # a m m o
    r'b[\s\.\-_]*u[\s\.\-_]*l[\s\.\-_]*l[\s\.\-_]*e[\s\.\-_]*t[\s\.\-_]*s?',  # b u l l e t s
    r'p[\s\.\-_]*i[\s\.\-_]*s[\s\.\-_]*t[\s\.\-_]*o[\s\.\-_]*l[\s\.\-_]*s?',  # p i s t o l s
    r'r[\s\.\-_]*i[\s\.\-_]*f[\s\.\-_]*l[\s\.\-_]*e[\s\.\-_]*s?',  # r i f l e s
    r'g[\s\.\-_]*r[\s\.\-_]*e[\s\.\-_]*n[\s\.\-_]*a[\s\.\-_]*d[\s\.\-_]*e[\s\.\-_]*s?',  # g r e n a d e s
    r'b[\s\.\-_]*o[\s\.\-_]*m[\s\.\-_]*b[\s\.\-_]*s?',  # b o m b s
    r'e[\s\.\-_]*x[\s\.\-_]*p[\s\.\-_]*l[\s\.\-_]*o[\s\.\-_]*s[\s\.\-_]*i[\s\.\-_]*v[\s\.\-_]*e[\s\.\-_]*s?',  # e x p l o s i v e s
]

# CP bypass patterns (critical for Telegram TOS protection)
CP_BYPASS_PATTERNS = [
    r'c[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*l[\s\.\-_]*d',  # c h i l d
    r'k[\s\.\-_]*i[\s\.\-_]*d[\s\.\-_]*s?',  # k i d s  
    r'l[\s\.\-_]*o[\s\.\-_]*l[\s\.\-_]*i',  # l o l i
    r'c[\s\.\-_]*p',  # c p
    r'p[\s\.\-_]*e[\s\.\-_]*d[\s\.\-_]*o',  # p e d o
    r's[\s\.\-_]*h[\s\.\-_]*o[\s\.\-_]*t[\s\.\-_]*a',  # s h o t a
    r'y[\s\.\-_]*o[\s\.\-_]*u[\s\.\-_]*n[\s\.\-_]*g',  # y o u n g (in certain contexts)
]

# Scam/Fraud bypass patterns
SCAM_BYPASS_PATTERNS = [
    r's[\s\.\-_]*c[\s\.\-_]*a[\s\.\-_]*m',  # s c a m
    r'f[\s\.\-_]*r[\s\.\-_]*a[\s\.\-_]*u[\s\.\-_]*d',  # f r a u d
    r'p[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*s[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # p h i s h i n g
    r'c[\s\.\-_]*a[\s\.\-_]*r[\s\.\-_]*d[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # c a r d i n g
    r'm[\s\.\-_]*o[\s\.\-_]*n[\s\.\-_]*e[\s\.\-_]*y[\s\.\-_]*l[\s\.\-_]*a[\s\.\-_]*u[\s\.\-_]*n[\s\.\-_]*d[\s\.\-_]*e[\s\.\-_]*r[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # m o n e y l a u n d e r i n g
]

class SecurityRuleEngine:
    """Security rule engine for content analysis with multi-message context tracking"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.compiled_patterns = self._compile_patterns()
        self.user_message_history = {}  # Track recent messages per user for context
    
    def _initialize_rules(self) -> Dict[str, ViolationRule]:
        """Initialize all security rules"""
        return {
            # CRITICAL - DELETE IN ALL MODES (LOW, MEDIUM, EXTREME)
            "child_exploitation": ViolationRule(
                category="child_exploitation",
                patterns=[
                    # English - Direct patterns
                    r"\b(cp|child\s*porn|kiddie\s*porn|pedo|loli|shota)\b",
                    r"\b(underage|minor|children?)\s*(sex|nude|naked|porn)",
                    r"\b(selling|trading|sharing|buy|purchase)\s*(cp|child\s*content)",
                    # Bypass attempts - ALL CP_BYPASS_PATTERNS
                    *CP_BYPASS_PATTERNS,
                    # Other languages (Hindi, Russian, Spanish, etc.)
                    r"\b(बच्चा|बच्चे|लड़का|लड़की)\s*(सेक्स|नंगा)",
                    r"\b(ребенок|дети|малолетк)\s*(секс|порно)",
                    r"\b(niño|niña|menor)\s*(sexo|porno)",
                    # Age-related selling
                    r"\b(young|teen|school)\s*(girl|boy)s?\s*(selling|available|for\s*sale)",
                ],
                bypass_patterns=CP_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Child exploitation and abuse content - TOS violation"
            ),
            
            # DRUG SELLING - DELETE IN LOW/MEDIUM/EXTREME
            "drug_selling": ViolationRule(
                category="drug_selling", 
                patterns=[
                    # Intentional selling/dealing - Direct patterns
                    r"\b(selling|dealing|buying|trading|purchase)\s*(weed|ganja|marijuana|cannabis|cocaine|heroin|meth|lsd|mdma|ecstasy)",
                    r"\b(drug\s*dealer|plug|supplier|vendor)\b",
                    r"\b(gram|ounce|kg|kilo|pound)\s*\$?\d+\s*(cocaine|heroin|meth|weed|ganja)",
                    r"\b(hit\s*me\s*up|dm\s*me|contact\s*me).*(weed|drugs|pills|cocaine|ganja)",
                    r"\b(wholesale|bulk|quantity)\s*(drugs|weed|ganja)",
                    # Bypass patterns - Separated words
                    *DRUG_BYPASS_PATTERNS,
                    *SELLING_BYPASS_PATTERNS,
                    # Combined bypass - selling + drugs in different patterns
                    r"(?=.*s[\s\.\-_]*e[\s\.\-_]*l[\s\.\-_]*l)(?=.*d[\s\.\-_]*r[\s\.\-_]*u[\s\.\-_]*g)",  # sell + drug anywhere
                    r"(?=.*b[\s\.\-_]*u[\s\.\-_]*y)(?=.*g[\s\.\-_]*a[\s\.\-_]*n[\s\.\-_]*j)",  # buy + ganja anywhere
                    # Multi-language
                    r"\b(बेचना|खरीदना)\s*(गांजा|चरस|हेरोइन)",
                    r"\b(продаю|покупаю|торгую)\s*(наркотики|марихуана|кокаин)",
                    r"\b(vendiendo|comprando|drogas|marihuana|cocaina)",
                ],
                bypass_patterns=DRUG_BYPASS_PATTERNS + SELLING_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Drug selling/distribution - TOS violation"
            ),
            
            # DRUG REFERENCES - DELETE IN MEDIUM/EXTREME ONLY
            "drug_references": ViolationRule(
                category="drug_references",
                patterns=[
                    # Any drug mention (casual or otherwise)
                    r"\b(weed|ganja|marijuana|cannabis|pot|herb|grass)\b",
                    r"\b(cocaine|coke|crack|heroin|smack|meth|crystal)\b", 
                    r"\b(lsd|acid|mdma|ecstasy|molly|pills|xanax)\b",
                    r"\b(charas|bhang|afeem|chitta)\b",  # Hindi/Urdu
                    r"\b(марихуана|кокаин|героин|наркотики)\b",  # Russian
                    r"\b(marihuana|cocaina|heroina|drogas)\b",  # Spanish
                    r"\b(吸毒|大麻|可卡因|海洛因)\b",  # Chinese
                    r"\b(マリファナ|コカイン|ヘロイン|薬物)\b",  # Japanese
                ],
                keywords=[
                    "weed", "ganja", "marijuana", "cannabis", "cocaine", "heroin",
                    "meth", "lsd", "ecstasy", "charas", "bhang", "afeem"
                ],
                severity=ViolationSeverity.MEDIUM,
                description="Drug references and casual mentions"
            ),
            
            # TELEGRAM ToS VIOLATIONS - DELETE IN MEDIUM/EXTREME
            "telegram_violations": ViolationRule(
                category="telegram_violations",
                patterns=[
                    r"\b(spam|scam|phishing|fake\s*account)\b",
                    r"\b(pyramid\s*scheme|ponzi|mlm|get\s*rich\s*quick)\b",
                    r"\b(copyright|pirated|cracked|hacked\s*software)\b",
                    r"\b(fake\s*news|misinformation|propaganda)\b",
                    r"\b(harassment|doxxing|stalking|threatening)\b",
                    r"\b(impersonation|identity\s*theft)\b",
                    # Multi-language ToS violations
                    r"\b(स्पैम|फर्जी|धोखाधड़ी)\b",  # Hindi
                    r"\b(спам|мошенничество|фейк)\b",  # Russian  
                    r"\b(estafa|spam|fraude|phishing)\b",  # Spanish
                ],
                keywords=[
                    "spam", "scam", "phishing", "pyramid scheme", "fake account",
                    "copyright violation", "harassment", "doxxing", "threats"
                ],
                severity=ViolationSeverity.HIGH,
                description="Telegram Terms of Service violations"
            ),
            
            # ABUSIVE CONTENT - DELETE IN EXTREME ONLY
            "abusive_content": ViolationRule(
                category="abusive_content", 
                patterns=[
                    r"\b(hate\s*speech|racist|discrimination)\b",
                    r"\b(bully|bullying|harassment|abuse)\b",
                    r"\b(threat|threatening|intimidation)\b",
                    r"\b(toxic|troll|trolling|flame\s*war)\b",
                    r"\b(sexist|homophobic|transphobic|bigot)\b",
                    # Unfair chat behavior
                    r"\b(spam\s*flood|raid|brigade)\b",
                    r"\b(off\s*topic|derail|disruption)\b",
                    # Multi-language abusive terms
                    r"\b(नफरत|गाली|धमकी|परेशानी)\b",  # Hindi
                    r"\b(ненависть|угрозы|оскорбление)\b",  # Russian
                    r"\b(odio|amenaza|acoso|insulto)\b",  # Spanish
                ],
                keywords=[
                    "hate speech", "racist", "bully", "harassment", "threats",
                    "toxic", "troll", "spam flood", "off topic", "disruption"
                ],
                severity=ViolationSeverity.MEDIUM,
                description="Abusive content and unfair chat behavior"
            ),
            
            # Weapons and Violence
            "weapons_violence": ViolationRule(
                category="weapons_violence",
                patterns=[
                    r"\b(selling|buying|trading)\s*(gun|weapon|firearm|rifle|pistol)",
                    r"\b(bomb|explosive|grenade|ammunition|ammo)\b",
                    r"\b(hit\s*man|assassin|killer\s*for\s*hire)",
                    r"\b(shoot|kill|murder|assassinate)\s*(someone|anybody)",
                ],
                keywords=[
                    "gun sales", "weapon dealer", "firearm", "ammunition",
                    "bomb", "explosive", "grenade", "hitman", "assassin"
                ],
                severity=ViolationSeverity.HIGH,
                description="Weapons sales and violent threats"
            ),
            
            # Hate Speech and Terrorism
            "hate_terrorism": ViolationRule(
                category="hate_terrorism",
                patterns=[
                    r"\b(nazi|hitler|holocaust\s*denial|white\s*supremacy)",
                    r"\b(terrorist|isis|al\s*qaeda|bomb\s*making)",
                    r"\b(kill\s*all|genocide|ethnic\s*cleansing)",
                    r"\b(join\s*our|recruitment).*(terrorist|extremist)",
                ],
                keywords=[
                    "nazi", "hitler", "white supremacy", "terrorist",
                    "isis", "al qaeda", "bomb making", "genocide",
                    "ethnic cleansing", "extremist recruitment"
                ],
                severity=ViolationSeverity.HIGH,
                description="Hate speech and terrorist content"
            ),
            
            # Fraud and Scams
            "fraud_scams": ViolationRule(
                category="fraud_scams",
                patterns=[
                    r"\b(bitcoin|crypto)\s*(doubling|investment|guaranteed)",
                    r"\b(phishing|fake\s*website|stolen\s*cards)",
                    r"\b(nigerian\s*prince|lottery\s*winner|inheritance)",
                    r"\b(ponzi|pyramid\s*scheme|mlm\s*scam)",
                ],
                keywords=[
                    "bitcoin doubling", "crypto scam", "phishing", 
                    "fake website", "stolen cards", "ponzi scheme",
                    "pyramid scheme", "nigerian prince", "lottery scam"
                ],
                severity=ViolationSeverity.MEDIUM,
                description="Fraudulent schemes and scams"
            ),
            
            # Spam and Unwanted Content  
            "spam_advertising": ViolationRule(
                category="spam_advertising",
                patterns=[
                    r"\b(join\s*my\s*channel|subscribe\s*to|follow\s*me)",
                    r"\b(advertisement|promotion|marketing|affiliate)",
                    r"\b(click\s*link|visit\s*website|buy\s*now)",
                    r"(telegram\.me|t\.me|@\w+)\s*(join|follow)",
                ],
                keywords=[
                    "advertisement", "promotion", "affiliate marketing",
                    "spam", "unsolicited", "bulk message", "chain letter"
                ],
                severity=ViolationSeverity.LOW,
                description="Spam and unwanted advertising"
            ),
            
            # Bot Detection Patterns
            "bot_behavior": ViolationRule(
                category="bot_behavior",
                patterns=[
                    r"^\[.*\]\s*.*\s*\[.*\]$",  # Bot-like formatting
                    r"^(/\w+\s*){2,}",  # Multiple commands
                    r"\b(bot|automated|script)\s*(message|response)",
                ],
                keywords=[
                    "automated message", "bot response", "script generated"
                ],
                severity=ViolationSeverity.LOW, 
                description="Bot-generated content detection"
            )
        }
    
    def _compile_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Compile regex patterns for efficiency"""
        compiled = {}
        for category, rule in self.rules.items():
            compiled[category] = [
                re.compile(pattern, rule.regex_flags) 
                for pattern in rule.patterns
            ]
        return compiled
    
    def analyze_message(self, text: str) -> List[Dict]:
        """Analyze message for violations"""
        violations = []
        text_lower = text.lower()
        
        for category, rule in self.rules.items():
            # Check keyword matches
            keyword_matches = [kw for kw in rule.keywords if kw.lower() in text_lower]
            
            # Check pattern matches  
            pattern_matches = []
            for pattern in self.compiled_patterns[category]:
                matches = pattern.findall(text)
                pattern_matches.extend(matches)
            
            if keyword_matches or pattern_matches:
                violations.append({
                    "category": category,
                    "severity": rule.severity.value,
                    "description": rule.description,
                    "keyword_matches": keyword_matches,
                    "pattern_matches": pattern_matches,
                    "confidence": self._calculate_confidence(
                        keyword_matches, pattern_matches, text
                    )
                })
        
        return violations
    
    def _calculate_confidence(self, keywords: List[str], patterns: List[str], text: str) -> float:
        """Calculate confidence score for violation detection"""
        base_score = 0.0
        
        # Keyword confidence
        if keywords:
            base_score += len(keywords) * 0.2
        
        # Pattern confidence  
        if patterns:
            base_score += len(patterns) * 0.3
        
        # Context analysis
        suspicious_context = self._analyze_context(text)
        base_score += suspicious_context * 0.3
        
        return min(base_score, 1.0)
    
    def _analyze_context(self, text: str) -> float:
        """Analyze message context for suspicious indicators"""
        suspicious_indicators = [
            "dm me", "hit me up", "private message", "contact me",
            "$", "price", "cheap", "deal", "offer", "selling",
            "urgent", "limited time", "act fast", "don't tell"
        ]
        
        text_lower = text.lower()
        matches = sum(1 for indicator in suspicious_indicators if indicator in text_lower)
        
        return matches / len(suspicious_indicators)
    
    def get_enforcement_action(self, violations: List[Dict], security_mode: SecurityMode) -> Dict:
        """Determine enforcement action based on violations and security mode"""
        if not violations:
            return {"action": "allow", "reason": "no_violations"}
        
        max_severity = max(v["severity"] for v in violations)
        has_critical = any(v["severity"] == "critical" for v in violations)
        
        # Critical violations always result in ban
        if has_critical:
            return {
                "action": "ban",
                "reason": "critical_violation",
                "delete_message": True,
                "notify_admin": True
            }
        
        # Security mode specific actions
        if security_mode == SecurityMode.EXTREME:
            if max_severity in ["high", "medium"]:
                return {
                    "action": "ban",
                    "reason": f"{max_severity}_violation_extreme_mode",
                    "delete_message": True,
                    "notify_admin": True
                }
            else:
                return {
                    "action": "warn",
                    "reason": "low_violation_extreme_mode", 
                    "delete_message": True
                }
        
        elif security_mode == SecurityMode.MEDIUM:
            if max_severity == "high":
                return {
                    "action": "restrict",
                    "reason": "high_violation_medium_mode",
                    "delete_message": True,
                    "duration": 24 * 60 * 60  # 24 hours
                }
            elif max_severity == "medium":
                return {
                    "action": "warn",
                    "reason": "medium_violation_medium_mode",
                    "delete_message": False
                }
            else:
                return {
                    "action": "log",
                    "reason": "low_violation_medium_mode"
                }
        
        else:  # LOW mode
            return {
                "action": "warn" if max_severity != "low" else "log",
                "reason": f"{max_severity}_violation_low_mode",
                "delete_message": False
            }

# Global rule engine instance
security_rules = SecurityRuleEngine()

# Exemption patterns (content that should not be flagged)
EXEMPTION_PATTERNS = [
    r"\b(drug\s*store|pharmacy|medicine|prescription)\b",  # Legitimate drug references
    r"\b(water\s*gun|toy\s*weapon|nerf\s*gun)\b",  # Toy weapons
    r"\b(history|documentary|news|education)\b.*\b(war|weapon|drug)\b",  # Educational content
]

def is_exempt_content(text: str) -> bool:
    """Check if content should be exempt from violation detection"""
    text_lower = text.lower()
    return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in EXEMPTION_PATTERNS)

def get_violation_summary(violations: List[Dict]) -> str:
    """Generate human-readable violation summary"""
    if not violations:
        return "No violations detected"
    
    categories = list(set(v["category"] for v in violations))
    severities = list(set(v["severity"] for v in violations))
    
    summary = f"Detected {len(violations)} violation(s) in categories: {', '.join(categories)}"
    if severities:
        summary += f" (Severity: {', '.join(severities)})"
    
    return summary

# Security Mode Configuration - What gets deleted at each level
SECURITY_MODE_RULES = {
    SecurityMode.LOW: {
        "delete_categories": [
            "child_exploitation",  # Always delete CP
            "drug_selling",       # Only intentional selling
        ],
        "description": "Only deletes serious violations: CP and intentional drug selling"
    },
    
    SecurityMode.MEDIUM: {
        "delete_categories": [
            "child_exploitation",   # Always delete CP
            "drug_selling",        # Intentional selling
            "drug_references",     # Any drug mentions (weed, ganja, etc.)
            "telegram_violations", # ToS violations in any language
        ],
        "description": "Deletes drug references, CP, ganja mentions, Telegram ToS violations"
    },
    
    SecurityMode.EXTREME: {
        "delete_categories": [
            "child_exploitation",   # Always delete CP
            "drug_selling",        # Intentional selling  
            "drug_references",     # Any drug mentions
            "telegram_violations", # ToS violations
            "abusive_content",     # Hate speech, harassment, unfair chat behavior
            "weapons_violence",    # Weapons content
            "hate_speech",         # Hate speech and extremism
        ],
        "description": "Deletes everything: all violations + abusive content + unfair chat behavior"
    }
}

def should_delete_message(violation_categories: List[str], security_mode: SecurityMode) -> bool:
    """
    Determine if message should be deleted based on security mode
    
    Args:
        violation_categories: List of detected violation categories
        security_mode: Current security mode
        
    Returns:
        True if message should be deleted, False otherwise
    """
    if not violation_categories:
        return False
        
    mode_rules = SECURITY_MODE_RULES.get(security_mode, {})
    delete_categories = mode_rules.get("delete_categories", [])
    
    # Check if any detected category is in the deletion list for this mode
    return any(category in delete_categories for category in violation_categories)