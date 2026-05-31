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

        try:
            ai_data = json.loads(cleaned_text)
            message_content = ai_data.get("message", "No message generated")
            parts_data = ai_data.get("parts", {})
            upgrades_data = ai_data.get("upgrades", {})
            benchmark_data = ai_data.get("benchmark", {})
            prices_data = ai_data.get("prices", {})
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
            "prices": prices_data 
        })
        
    except Exception as e:
        print(f"General Server Crash Error: {e}")
        return jsonify({"error": str(e)}), 500
    
    
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)