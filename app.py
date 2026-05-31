import os
import json 
import re  # Added regular expressions module to sanitize raw strings
from flask import Flask, request, jsonify, render_template  
from flask_cors import CORS
import google.generativeai as genai
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
CORS(app) 

# --- DATABASE CONFIGURATION (DUAL-MODE) ---
# When deployed to Railway, it reads DATABASE_URL. Locally, it connects to your local PostgreSQL engine.
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Use your local PostgreSQL instead of SQLite now!
    DATABASE_URL = "***REMOVED***"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE SCHEMA (LAYOUT TABLE) ---
# LEAVE THIS EXACTLY AS IT WAS - Flask needs this to construct the database rules!
class PCBuild(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    response = db.Column(db.Text, nullable=False)        # Conversational Markdown response
    parts = db.Column(db.Text)                           # Stringified JSON block
    prices = db.Column(db.Text)                          # Stringified JSON block
    upgrades = db.Column(db.Text)                        # Stringified JSON block
    benchmark = db.Column(db.Text)                       # Stringified JSON block
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Automatically generate database tables inside app environment context
with app.app_context():
    db.create_all()

# Securely grab the API key from Railway's environment variables
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 1. Update the persona with STRICT JSON rules
ramsey_persona = """
You are Ramsey, an expert PC building assistant and hardware technician. 
Your primary goal is to help users design custom PCs. 

CRITICAL INSTRUCTION: You MUST ALWAYS respond strictly in JSON format. Your response must be a single valid JSON object structured exactly like this:
{
    "message": "Your FULL conversational response in Markdown. ALWAYS structure your response exactly like this:\n\n1. A short 2-3 sentence intro about the build.\n\n2. The parts list:\n**CPU:** [Part Name] — ₱[price] (via [source])\n**GPU:** [Part Name] — ₱[price] (via [source])\n**Motherboard:** [Part Name] — ₱[price] (via [source])\n**RAM:** [Part Name] — ₱[price] (via [source])\n**Storage:** [Part Name] — ₱[price] (via [source])\n**Power Supply:** [Part Name] — ₱[price] (via [source])\n**Case:** [Part Name] — ₱[price] (via [source])\n\n3. **Total Estimate: ₱[sum]**\n\n4. A short closing line about what the build is best for. Never skip prices.",
    "parts": {
        "CPU": "Part name or null",
        "GPU": "Part name or null",
        "Motherboard": "Part name or null",
        "RAM": "Part name or null",
        "Storage": "Part name or null",
        "Power Supply": "Part name or null",
        "Case": "Part name or null"
    },
    "prices": {
        "CPU": {"price": "₱XXXX", "source": "Shopee / PC Express"},
        "GPU": {"price": "₱XXXX", "source": "Lazada / EasyPC"},
        "Motherboard": {"price": "₱XXXX", "source": "Dynaquest"},
        "RAM": {"price": "₱XXXX", "source": "Shopee"},
        "Storage": {"price": "₱XXXX", "source": "PC Express"},
        "Power Supply": {"price": "₱XXXX", "source": "EasyPC"},
        "Case": {"price": "₱XXXX", "source": "Lazada"},
        "total_estimate": "₱XXXX"
    },
    "upgrades": {
        "keep": ["Item to keep or reuse", "..."],
        "replace_first": ["Highest impact upgrade with reason", "..."],
        "delay": ["Low priority upgrade", "..."]
    },
    "benchmark": {
        "gaming": {
            "score": 85,
            "label": "Strong",
            "description": "One sentence about gaming performance at the target resolution.",
            "games_good": ["Game A", "Game B", "Game C"],
            "games_bad": ["Game X", "Game Y"]
        },
        "work": {
            "score": 70,
            "label": "Good",
            "description": "One sentence about productivity/content creation performance."
        },
        "upgradability": {
            "score": 75,
            "label": "Healthy",
            "description": "One sentence about future upgrade potential."
        }
    }
}

BENCHMARK RULES:
- "score" is an integer from 0 to 100 representing estimated suitability. Be realistic and accurate.
  - 90-100: Exceptional / Overkill
  - 75-89: Strong / High
  - 55-74: Good / Capable
  - 35-54: Moderate / Limited
  - 0-34: Weak / Poor
- "label" must match the score range: use "Exceptional", "Strong", "Good", "Moderate", or "Weak".
- "games_good": 3–5 real game titles the build runs well at the user's target resolution/settings.
- "games_bad": 2–3 real game titles the build will struggle with (low fps or needs reduced settings).
- Always populate benchmark with realistic estimates based on the recommended or discussed parts.
- If no build has been discussed yet, use neutral mid-range scores (50) with a note to ask for a build.

PARTS RULES:
- Fill "parts" only when actively recommending a build. Otherwise set values to null.

UPGRADES RULES:
- Fill "upgrades" with practical advice based on the build or the user's current setup.
  - "keep": components worth reusing or not replacing.
  - "replace_first": the highest-impact upgrades — explain WHY briefly.
  - "delay": things that can wait or aren't worth it yet.
- Each array should have 1–3 short, specific bullet items.

PRICING RULES:
- Always fill "prices" when recommending parts.
- Use realistic Philippine Peso (₱) prices based on current market rates from local stores.
- Sources to reference: PC Express, EasyPC, Dynaquest, Shopee, Lazada, Octagon, Silicon Valley PH.
- Pick the most likely/common source where Filipinos actually buy that part.
- "total_estimate" is the sum of all parts.
- If a part is null, set its price entry to null too.

- Do not include any text outside this JSON object.
"""

# 2. Force Gemini into JSON mode
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=ramsey_persona,
    generation_config={"response_mime_type": "application/json"}
)
chat = model.start_chat(history=[])

# --- WEB APPLICATION ROUTE IMPLEMENTATIONS ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/history', methods=['GET'])
def get_build_history():
    try:
        # 1. Fetch all build records from your PostgreSQL table, newest first
        builds = PCBuild.query.order_by(PCBuild.created_at.desc()).all()
        
        # 2. Format the rows into a clean list of dictionaries for the frontend
        history_list = []
        for build in builds:
            history_list.append({
                "id": build.id,
                "title": build.title,
                "description": build.description,
                "parts": json.loads(build.parts) if build.parts else {},
                "prices": json.loads(build.prices) if build.prices else {},
                "upgrades": json.loads(build.upgrades) if build.upgrades else {},
                "benchmark": json.loads(build.benchmark) if build.benchmark else {},
                "response": build.response,
                "created_at": build.created_at.strftime("%b %d, %Y")
            })
            
        return jsonify(history_list), 200

    except Exception as e:
        print(f"❌ HISTORY FETCH ERROR: {e}")
        return jsonify({"error": "Could not retrieve history data"}), 500


@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_input = data.get('message')
    
    if not user_input:
        return jsonify({"error": "No message provided"}), 400
    
    try:
        response = chat.send_message(user_input)
        raw_text = response.text
        
        # Clean out loose raw control characters
        cleaned_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)
        
        # Fallbacks if the AI sends plain prose text instead of full JSON layouts
        message_content = cleaned_text
        parts_data = {}
        upgrades_data = {}
        benchmark_data = {}
        prices_data = {}

        # Safe try-parse block to split structured JSON attributes if available
        try:
            ai_data = json.loads(cleaned_text)
            message_content = ai_data.get("message", "No message generated")
            parts_data = ai_data.get("parts", {})
            upgrades_data = ai_data.get("upgrades", {})
            benchmark_data = ai_data.get("benchmark", {})
            prices_data = ai_data.get("prices", {})
        except json.JSONDecodeError:
            print("💡 Info: AI response parsed as markdown formatting string.")

        # --- 💾 POSTGRESQL DATABASE WRITER BLOCK ---
        new_build = PCBuild(
            title=user_input[:100],  
            description="Generated via Web UI Dashboard",
            response=message_content,
            parts=json.dumps(parts_data),
            prices=json.dumps(prices_data),
            upgrades=json.dumps(upgrades_data),
            benchmark=json.dumps(benchmark_data)
        )
        
        try:
            db.session.add(new_build)
            db.session.commit()
            print("🎉 SUCCESS: Saved configuration directly to PostgreSQL!")
        except Exception as db_err:
            db.session.rollback()
            print(f"❌ DATABASE TRANSACTION REJECTED: {db_err}")
        # --------------------------------------------

        return jsonify({
            "response": message_content,
            "parts": parts_data,
            "upgrades": upgrades_data,
            "benchmark": benchmark_data,
            "prices": prices_data 
        })
        
    except Exception as e:
        print(f"General Server Crash Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)