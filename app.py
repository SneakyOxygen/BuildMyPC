import os
import json 
import re  # Added regular expressions module to sanitize raw strings
from flask import Flask, request, jsonify, render_template  
from flask_cors import CORS
import google.generativeai as genai
# 1. COMMENT OUT SQLALCHEMY IMPORT BELOW IF DESIRED (Optional, but safe to keep or remove)
# from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
CORS(app) 

# --- DATABASE CONFIGURATION (OFFLINE MODE) ---
# DATABASE_URL = os.environ.get("DATABASE_URL")
# if not DATABASE_URL:
#     DATABASE_URL = "postgresql://postgres:admin123@localhost:5432/ramsey_db"
# if DATABASE_URL.startswith("postgres://"):
#     DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)


# --- DATABASE SCHEMA (COMMENTED OUT FOR NO-DB TESTING) ---
# class PCBuild(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     title = db.Column(db.String(100), nullable=False)
#     description = db.Column(db.String(200))
#     response = db.Column(db.Text, nullable=False)        
#     parts = db.Column(db.Text)                           
#     prices = db.Column(db.Text)                          
#     upgrades = db.Column(db.Text)                        
#     benchmark = db.Column(db.Text)                       
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)


# --- TABLE SETUP CONTEXT (COMMENTED OUT) ---
# with app.app_context():
#     db.create_all()

# Securely grab the API key from Railway's environment variables
api_key = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=api_key)

# 1. Update the persona with STRICT JSON rules
ramsey_persona = """
You are Ramsey, a sharp and friendly PC building expert for Filipino buyers.
You MUST always respond with a single valid JSON object. No text outside the JSON. Ever.

RESPONSE FORMAT depends on what the user asked:

--- IF user asks for a build or parts recommendation ---
"message" must follow this exact structure (use real newlines between sections):

One sentence intro about what the build targets.

**CPU:** [Name] — ₱[price] (via [source])
**GPU:** [Name] — ₱[price] (via [source])
**Motherboard:** [Name] — ₱[price] (via [source])
**RAM:** [Name] — ₱[price] (via [source])
**Storage:** [Name] — ₱[price] (via [source])
**Power Supply:** [Name] — ₱[price] (via [source])
**Case:** [Name] — ₱[price] (via [source])

**Total Estimate: ₱[sum]**

One sentence on what this build is best for.

Fill parts, prices, upgrades, and benchmark fully.

--- IF user asks a question, follow-up, or comparison (no new build needed) ---
Answer in 2-4 short paragraphs. No parts list. Be direct.
Set parts, prices, upgrades, benchmark all to null.

JSON STRUCTURE (always return this exact shape):
{
    "message": "Markdown response here",
    "suggested_phrases": [
        "A short follow-up question or action the user might want next",
        "Another relevant follow-up",
        "A third option"
    ],
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
        "CPU": {"price": "₱XXXX", "source": "Store name"},
        "GPU": {"price": "₱XXXX", "source": "Store name"},
        "Motherboard": {"price": "₱XXXX", "source": "Store name"},
        "RAM": {"price": "₱XXXX", "source": "Store name"},
        "Storage": {"price": "₱XXXX", "source": "Store name"},
        "Power Supply": {"price": "₱XXXX", "source": "Store name"},
        "Case": {"price": "₱XXXX", "source": "Store name"},
        "total_estimate": "₱XXXX"
    },
    "upgrades": {
        "keep": ["Component — reason"],
        "replace_first": ["Component — reason"],
        "delay": ["Component — reason"]
    },
    "benchmark": {
        "gaming": {
            "score": 85,
            "label": "Strong",
            "description": "One sentence on gaming performance.",
            "games_good": ["Game A", "Game B", "Game C"],
            "games_bad": ["Game X", "Game Y"]
        },
        "work": {
            "score": 70,
            "label": "Good",
            "description": "One sentence on productivity performance."
        },
        "upgradability": {
            "score": 75,
            "label": "Healthy",
            "description": "One sentence on upgrade potential."
        }
    }
}

RULES:
- scores 90-100: Exceptional, 75-89: Strong, 55-74: Good, 35-54: Moderate, 0-34: Weak.
- games_good: 3-5 real titles the build runs well. games_bad: ALWAYS include 2-3 real titles the build will struggle with — never leave this empty on a build recommendation.
- Use real Philippine Peso prices from: PC Express, EasyPC, Dynaquest, Shopee, Lazada, Octagon.
- suggested_phrases: always 3 short follow-up actions tailored to what was just discussed. For builds: things like "Show a cheaper GPU option", "Make this build quieter", "What can I upgrade first?". For Q&A: natural next questions. Each phrase should be under 8 words and work as a standalone prompt.
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
        # Return an empty mock list so the frontend doesn't break trying to map over nothing
        return jsonify([]), 200

        # --- COMMENTED OUT REAL DB QUERIES ---
        # builds = PCBuild.query.order_by(PCBuild.created_at.desc()).all()
        # history_list = []
        # for build in builds:
        #     history_list.append({
        #         "id": build.id,
        #         "title": build.title,
        #         "description": build.description,
        #         "parts": json.loads(build.parts) if build.parts else {},
        #         "prices": json.loads(build.prices) if build.prices else {},
        #         "upgrades": json.loads(build.upgrades) if build.upgrades else {},
        #         "benchmark": json.loads(build.benchmark) if build.benchmark else {},
        #         "response": build.response,
        #         "created_at": build.created_at.strftime("%b %d, %Y")
        #     })
        # return jsonify(history_list), 200
        # -------------------------------------

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
        
        cleaned_text = re.sub(r'[\x00-\x1F\x7F]', '', raw_text)
        
        message_content = cleaned_text
        parts_data = {}
        upgrades_data = {}
        benchmark_data = {}
        prices_data = {}
        suggested_phrases = []

        try:
            ai_data = json.loads(cleaned_text)
            message_content = ai_data.get("message", "No message generated")
            parts_data = ai_data.get("parts", {})
            upgrades_data = ai_data.get("upgrades", {})
            benchmark_data = ai_data.get("benchmark", {})
            prices_data = ai_data.get("prices", {})
            suggested_phrases = ai_data.get("suggested_phrases", [])
        except json.JSONDecodeError:
            print("💡 Info: AI response parsed as markdown formatting string.")

        # --- 💾 COMMENTED OUT POSTGRESQL DATABASE WRITER BLOCK ---
        # new_build = PCBuild(
        #     title=user_input[:100],  
        #     description="Generated via Web UI Dashboard",
        #     response=message_content,
        #     parts=json.dumps(parts_data),
        #     prices=json.dumps(prices_data),
        #     upgrades=json.dumps(upgrades_data),
        #     benchmark=json.dumps(benchmark_data)
        # )
        # try:
        #     db.session.add(new_build)
        #     db.session.commit()
        #     print("🎉 SUCCESS: Saved configuration directly to PostgreSQL!")
        # except Exception as db_err:
        #     db.session.rollback()
        #     print(f"❌ DATABASE TRANSACTION REJECTED: {db_err}")
        # --------------------------------------------------------

        return jsonify({
            "response": message_content,
            "parts": parts_data,
            "upgrades": upgrades_data,
            "benchmark": benchmark_data,
            "prices": prices_data,
            "suggested_phrases": suggested_phrases
        })
        
    except Exception as e:
        print(f"General Server Crash Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, ssl_context='adhoc')