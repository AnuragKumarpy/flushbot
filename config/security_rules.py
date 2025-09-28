"""
Enhanced Security Rules with Comprehensive TOS Protection
Designed to minimize API usage and protect groups from Telegram moderation
"""

import re
from typing import Dict, List, Tuple, Optional
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

# Comprehensive TOS Violations Database - Protect Groups from Telegram Bans
# Patterns designed to catch bypass attempts and multi-message splitting

# Drug-related bypass patterns for split messages - more precise
DRUG_BYPASS_PATTERNS = [
    r'\bd[\s\.\-_]+r[\s\.\-_]+u[\s\.\-_]+g[\s\.\-_]*s?\b',  # d r u g s
    r'\bw[\s\.\-_]+e[\s\.\-_]+e[\s\.\-_]+d\b',  # w e e d  
    r'\bc[\s\.\-_]+o[\s\.\-_]+k[\s\.\-_]+e\b',  # c o k e
    r'\bm[\s\.\-_]+e[\s\.\-_]+t[\s\.\-_]+h\b',  # m e t h
    r'\bh[\s\.\-_]+e[\s\.\-_]+r[\s\.\-_]+o[\s\.\-_]+i[\s\.\-_]+n\b',  # h e r o i n
    r'\bg[\s\.\-_]+a[\s\.\-_]+n[\s\.\-_]+j[\s\.\-_]+a\b',  # g a n j a
    r'\bm[\s\.\-_]+d[\s\.\-_]+m[\s\.\-_]+a\b',  # m d m a
    r'\bl[\s\.\-_]+s[\s\.\-_]+d\b',  # l s d
    r'\bx[\s\.\-_]+t[\s\.\-_]+c\b',  # x t c / ecstasy
    r'\bo[\s\.\-_]+p[\s\.\-_]+i[\s\.\-_]+u[\s\.\-_]+m\b',  # o p i u m
    r'\bc[\s\.\-_]+r[\s\.\-_]+a[\s\.\-_]+c[\s\.\-_]+k\b',  # c r a c k
    r'\bh[\s\.\-_]+a[\s\.\-_]+s[\s\.\-_]+h[\s\.\-_]+i[\s\.\-_]+s[\s\.\-_]+h\b',  # h a s h i s h
]

# Selling/Trading bypass patterns - more precise
SELLING_BYPASS_PATTERNS = [
    r'\bs[\s\.\-_]+e[\s\.\-_]+l[\s\.\-_]+l[\s\.\-_]+i[\s\.\-_]+n[\s\.\-_]+g\b',  # s e l l i n g
    r'\bf[\s\.\-_]+o[\s\.\-_]+r[\s\.\-_]+s[\s\.\-_]+a[\s\.\-_]+l[\s\.\-_]+e\b',  # f o r s a l e
    r'\bb[\s\.\-_]+u[\s\.\-_]+y[\s\.\-_]+i[\s\.\-_]+n[\s\.\-_]+g\b',  # b u y i n g
    r'\bt[\s\.\-_]+r[\s\.\-_]+a[\s\.\-_]+d[\s\.\-_]+e\b',  # t r a d e
    r'\ba[\s\.\-_]+v[\s\.\-_]+a[\s\.\-_]+i[\s\.\-_]+l[\s\.\-_]+a[\s\.\-_]+b[\s\.\-_]+l[\s\.\-_]+e\b',  # a v a i l a b l e
    r'\bw[\s\.\-_]+a[\s\.\-_]+n[\s\.\-_]+t[\s\.\-_]+e[\s\.\-_]+d\b',  # w a n t e d
]

# Weapons bypass patterns - more precise
WEAPONS_BYPASS_PATTERNS = [
    r'\bg[\s\.\-_]+u[\s\.\-_]+n[\s\.\-_]*s?\b',  # g u n s
    r'\bw[\s\.\-_]+e[\s\.\-_]+a[\s\.\-_]+p[\s\.\-_]+o[\s\.\-_]+n[\s\.\-_]*s?\b',  # w e a p o n s
    r'\ba[\s\.\-_]+m[\s\.\-_]+m[\s\.\-_]+o\b',  # a m m o
    r'\bb[\s\.\-_]+u[\s\.\-_]+l[\s\.\-_]+l[\s\.\-_]+e[\s\.\-_]+t[\s\.\-_]*s?\b',  # b u l l e t s
    r'\bp[\s\.\-_]+i[\s\.\-_]+s[\s\.\-_]+t[\s\.\-_]+o[\s\.\-_]+l[\s\.\-_]*s?\b',  # p i s t o l s
    r'\br[\s\.\-_]+i[\s\.\-_]+f[\s\.\-_]+l[\s\.\-_]+e[\s\.\-_]*s?\b',  # r i f l e s
    r'\bg[\s\.\-_]+r[\s\.\-_]+e[\s\.\-_]+n[\s\.\-_]+a[\s\.\-_]+d[\s\.\-_]+e[\s\.\-_]*s?\b',  # g r e n a d e s
    r'\bb[\s\.\-_]+o[\s\.\-_]+m[\s\.\-_]+b[\s\.\-_]*s?\b',  # b o m b s
    r'\be[\s\.\-_]+x[\s\.\-_]+p[\s\.\-_]+l[\s\.\-_]+o[\s\.\-_]+s[\s\.\-_]+i[\s\.\-_]+v[\s\.\-_]+e[\s\.\-_]*s?\b',  # e x p l o s i v e s
]

# CP bypass patterns (critical for Telegram TOS protection) - more precise
CP_BYPASS_PATTERNS = [
    r'\bc[\s\.\-_]+h[\s\.\-_]+i[\s\.\-_]+l[\s\.\-_]+d\b',  # c h i l d
    r'\bk[\s\.\-_]+i[\s\.\-_]+d[\s\.\-_]*s?\b',  # k i d s  
    r'\bl[\s\.\-_]+o[\s\.\-_]+l[\s\.\-_]+i\b',  # l o l i
    r'\bc[\s\.\-_]+p\b',  # c p
    r'\bp[\s\.\-_]+e[\s\.\-_]+d[\s\.\-_]+o\b',  # p e d o
    r'\bs[\s\.\-_]+h[\s\.\-_]+o[\s\.\-_]+t[\s\.\-_]+a\b',  # s h o t a
]

# Scam/Fraud bypass patterns
SCAM_BYPASS_PATTERNS = [
    r's[\s\.\-_]*c[\s\.\-_]*a[\s\.\-_]*m',  # s c a m
    r'f[\s\.\-_]*r[\s\.\-_]*a[\s\.\-_]*u[\s\.\-_]*d',  # f r a u d
    r'p[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*s[\s\.\-_]*h[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # p h i s h i n g
    r'c[\s\.\-_]*a[\s\.\-_]*r[\s\.\-_]*d[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # c a r d i n g
    r'm[\s\.\-_]*o[\s\.\-_]*n[\s\.\-_]*e[\s\.\-_]*y[\s\.\-_]*l[\s\.\-_]*a[\s\.\-_]*u[\s\.\-_]*n[\s\.\-_]*d[\s\.\-_]*e[\s\.\-_]*r[\s\.\-_]*i[\s\.\-_]*n[\s\.\-_]*g',  # m o n e y l a u n d e r i n g
]

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

class MultiMessageTracker:
    """Tracks messages across users to detect split violations"""
    
    def __init__(self):
        self.user_history = {}  # user_id -> [recent_messages]
        self.max_history = 5   # Track last 5 messages per user
        self.time_window = 300  # 5 minutes window
    
    def add_message(self, user_id: int, text: str, timestamp):
        """Add message to user history"""
        if user_id not in self.user_history:
            self.user_history[user_id] = []
        
        # Add new message
        self.user_history[user_id].append({
            'text': text,
            'timestamp': timestamp
        })
        
        # Keep only recent messages
        self.user_history[user_id] = self.user_history[user_id][-self.max_history:]
    
    def check_split_violations(self, user_id: int) -> List[str]:
        """Check if user's recent messages form split violations"""
        if user_id not in self.user_history:
            return []
        
        recent_messages = self.user_history[user_id]
        if len(recent_messages) < 2:
            return []
        
        # Combine recent messages
        combined_text = " ".join([msg['text'] for msg in recent_messages])
        
        violations = []
        
        # More precise split detection - require both drug AND selling patterns
        drug_found = any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in DRUG_BYPASS_PATTERNS)
        selling_found = any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in SELLING_BYPASS_PATTERNS)
        
        if drug_found and selling_found:
            violations.append("drug_selling_split")
        
        # Check for split weapon + selling patterns
        weapon_found = any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in WEAPONS_BYPASS_PATTERNS)
        
        if weapon_found and selling_found:
            violations.append("weapon_selling_split")
        
        # Check for split CP patterns - require CP pattern + selling
        cp_found = any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in CP_BYPASS_PATTERNS)
        
        if cp_found and selling_found:
            violations.append("child_exploitation_split")
        
        return violations

class SecurityRuleEngine:
    """Security rule engine for content analysis with multi-message context tracking"""
    
    def __init__(self):
        self.rules = self._initialize_rules()
        self.compiled_patterns = self._compile_patterns()
        self.message_tracker = MultiMessageTracker()
    
    def _initialize_rules(self) -> Dict[str, ViolationRule]:
        """Initialize comprehensive TOS protection rules"""
        return {
            # CRITICAL - DELETE IN ALL MODES (LOW, MEDIUM, EXTREME) - PROTECT FROM TELEGRAM BANS
            "child_exploitation": ViolationRule(
                category="child_exploitation",
                patterns=[
                    # Direct patterns
                    r"\b(cp|child\s*porn|kiddie\s*porn|pedo|loli|shota)\b",
                    r"\b(underage|minor|children?)\s*(sex|nude|naked|porn)",
                    r"\b(selling|trading|sharing|buy|purchase)\s*(cp|child\s*content)",
                    # Bypass patterns
                    *CP_BYPASS_PATTERNS,
                    # Multi-language
                    r"\b(बच्चा|बच्चे|लड़का|लड़की)\s*(सेक्स|नंगा)",
                    r"\b(ребенок|дети|малолетк)\s*(секс|порно)",
                    r"\b(niño|niña|menor)\s*(sexo|porno)",
                    # Age-related selling
                    r"\b(young|teen|school)\s*(girl|boy)s?\s*(selling|available|for\s*sale)",
                ],
                bypass_patterns=CP_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Child exploitation - Critical TOS violation"
            ),
            
            "drug_selling": ViolationRule(
                category="drug_selling", 
                patterns=[
                    # Direct selling patterns - GENERIC DRUGS
                    r"\b(selling|dealing|buying|trading|purchase|sell)\s+(drugs?|substances?|narcotics?)",
                    r"\b(drugs?|substances?|narcotics?)\s+(selling|dealing|buying|trading|for\s*sale|available)",
                    # Specific drug selling
                    r"\b(selling|dealing|buying|trading|purchase)\s*(weed|ganja|marijuana|cannabis|cocaine|heroin|meth|lsd|mdma|ecstasy)",
                    r"\b(drug\s*dealer|plug|supplier|vendor)\b",
                    r"\b(gram|ounce|kg|kilo|pound)\s*\$?\d+\s*(cocaine|heroin|meth|weed|ganja)",
                    r"\b(hit\s*me\s*up|dm\s*me|contact\s*me).*(weed|drugs|pills|cocaine|ganja)",
                    r"\b(wholesale|bulk|quantity)\s*(drugs|weed|ganja)",
                    # Bypass patterns
                    *DRUG_BYPASS_PATTERNS,
                    *SELLING_BYPASS_PATTERNS,
                    # Combined bypass detection
                    r"(?=.*(" + "|".join(DRUG_BYPASS_PATTERNS) + r"))(?=.*(" + "|".join(SELLING_BYPASS_PATTERNS) + r"))",
                    # Multi-language
                    r"\b(बेचना|खरीदना)\s*(गांजा|चरस|हेरोइन)",
                    r"\b(продаю|покупаю|торгую)\s*(наркотики|марихуана|кокаин)",
                    r"\b(vendiendo|comprando|drogas|marihuana|cocaina)",
                ],
                bypass_patterns=DRUG_BYPASS_PATTERNS + SELLING_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Drug selling/distribution - Critical TOS violation"
            ),
            
            "weapon_selling": ViolationRule(
                category="weapon_selling",
                patterns=[
                    # Direct weapon selling
                    r"\b(selling|buying|trading|dealing)\s*(guns?|weapons?|firearms?|ammunition|ammo)",
                    r"\b(pistol|rifle|shotgun|ak47|ar15|glock|bullets?|grenades?)\s*(for\s*sale|selling|available)",
                    r"\b(gun\s*dealer|arms\s*dealer|weapons?\s*supplier)",
                    r"\b(explosives?|bombs?|c4|dynamite)\s*(selling|available|for\s*sale)",
                    # Bypass patterns
                    *WEAPONS_BYPASS_PATTERNS,
                    # Combined bypass
                    r"(?=.*(" + "|".join(WEAPONS_BYPASS_PATTERNS) + r"))(?=.*(" + "|".join(SELLING_BYPASS_PATTERNS) + r"))",
                    # Multi-language
                    r"\b(बेचना|खरीदना)\s*(बंदूक|हथियार)",
                    r"\b(продаю|покупаю)\s*(оружие|пистолет|автомат)",
                    r"\b(vendiendo|comprando)\s*(armas|pistola|fusil)",
                ],
                bypass_patterns=WEAPONS_BYPASS_PATTERNS + SELLING_BYPASS_PATTERNS,
                severity=ViolationSeverity.CRITICAL,
                description="Weapon selling - Critical TOS violation"
            ),
            
            # MEDIUM+ VIOLATIONS
            "scam_fraud": ViolationRule(
                category="scam_fraud",
                patterns=[
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
                description="Scam/fraud - TOS violation"
            ),
            
            "telegram_violations": ViolationRule(
                category="telegram_violations",
                patterns=[
                    r"\b(spam|phishing|fake\s*account)\b",
                    r"\b(pyramid\s*scheme|ponzi|mlm|get\s*rich\s*quick)\b",
                    r"\b(copyright|pirated|cracked|hacked\s*software)\b",
                    r"\b(fake\s*news|misinformation|propaganda)\b",
                    r"\b(harassment|doxxing|stalking|threatening)\b",
                    r"\b(impersonation|identity\s*theft)\b",
                    # Multi-language
                    r"\b(स्पैम|फर्जी|धोखाधड़ी)\b",
                    r"\b(спам|мошенничество|фейк)\b",
                    r"\b(estafa|spam|fraude|phishing)\b",
                ],
                severity=ViolationSeverity.HIGH,
                description="Telegram TOS violations"
            ),
            
            # EXTREME ONLY - ABUSIVE CONTENT
            "abusive_content": ViolationRule(
                category="abusive_content",
                patterns=[
                    r"\b(hate\s*speech|racist|discrimination|nazi|fascist)\b",
                    r"\b(bully|bullying|harassment|abuse|toxic|troll)\b",
                    r"\b(threat|threatening|intimidation|violence)\b",
                    r"\b(sexist|homophobic|transphobic|bigot)\b",
                    r"\b(spam\s*flood|raid|brigade|derail)\b",
                    # Multi-language
                    r"\b(नफरत|गाली|धमकी|परेशानी)\b",
                    r"\b(ненависть|угрозы|оскорбление)\b",
                    r"\b(odio|amenaza|acoso|insulto)\b",
                ],
                severity=ViolationSeverity.MEDIUM,
                description="Abusive content - extreme mode only"
            ),
        }
    
    def _compile_patterns(self) -> Dict[str, List]:
        """Compile regex patterns for better performance"""
        compiled = {}
        for category, rule in self.rules.items():
            compiled[category] = [
                re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                for pattern in rule.patterns
            ]
        return compiled
    
    def analyze_message(self, text: str, user_id: int = None, timestamp=None) -> List[Dict]:
        """Analyze message for violations with multi-message context"""
        violations = []
        
        # Add to message history for context tracking
        if user_id and timestamp:
            self.message_tracker.add_message(user_id, text, timestamp)
        
        # Check current message
        for category, patterns in self.compiled_patterns.items():
            rule = self.rules[category]
            
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    violations.append({
                        "category": category,
                        "severity": rule.severity.value,
                        "confidence": rule.confidence,
                        "description": rule.description,
                        "matched_text": matches[0] if isinstance(matches[0], str) else str(matches[0]),
                        "pattern_type": "direct"
                    })
                    break  # One match per category is enough
        
        # Check split violations across recent messages (only if no direct violations found)
        if user_id and not violations:  # Only check split if no direct violations
            split_violations = self.message_tracker.check_split_violations(user_id)
            for split_cat in split_violations:
                violations.append({
                    "category": split_cat,
                    "severity": "critical",
                    "confidence": 0.9,
                    "description": f"Split message violation: {split_cat}",
                    "matched_text": "multi-message pattern",
                    "pattern_type": "split"
                })
        
        return violations

# Security Mode Configuration
SECURITY_MODE_RULES = {
    SecurityMode.LOW: {
        "delete_categories": [
            "child_exploitation",
            "drug_selling", 
            "weapon_selling",
        ],
        "description": "Critical TOS violations only - protect from Telegram bans"
    },
    SecurityMode.MEDIUM: {
        "delete_categories": [
            "child_exploitation",
            "drug_selling",
            "weapon_selling", 
            "scam_fraud",
            "telegram_violations",
        ],
        "description": "All TOS violations + scams/fraud"
    },
    SecurityMode.EXTREME: {
        "delete_categories": [
            "child_exploitation",
            "drug_selling",
            "weapon_selling",
            "scam_fraud", 
            "telegram_violations",
            "abusive_content",
        ],
        "description": "All violations including abusive content - NO BANS, only silent deletion"
    }
}

def should_delete_message(violation_categories: List[str], security_mode: SecurityMode) -> bool:
    """Determine if message should be deleted based on security mode"""
    delete_categories = SECURITY_MODE_RULES[security_mode]["delete_categories"]
    
    # Check for split violations
    split_categories = [cat for cat in violation_categories if cat.endswith("_split")]
    if split_categories:
        # Split violations are always critical
        base_categories = [cat.replace("_split", "") for cat in split_categories]
        return any(category in delete_categories for category in base_categories)
    
    return any(category in delete_categories for category in violation_categories)

def is_exempt_content(text: str) -> bool:
    """Check if content should be exempt from analysis"""
    exempt_patterns = [
        r"^/\w+",  # Bot commands
        r"^\s*$",  # Empty messages
        r"^https?://",  # URLs only
        r"^@\w+",  # Mentions only
    ]
    
    return any(re.match(pattern, text.strip()) for pattern in exempt_patterns)

# Initialize the security rule engine
security_rules = SecurityRuleEngine()