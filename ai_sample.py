# do this pip install --upgrade google-generativeai
# and this pip install google.generativeai
# and this pip install SpeechRecognition
# and this pip install pipwin ONLY for Windows systems
# then this pip install pyaudio
# and this pip install pyttsx3 (text to speech)

# next, go to aistudio.google.com
# find "Get API key" located at the bottom left
# then copy your API key
# paste it in the api_key=

'''
    To install Pyaudio in Linux distributions, 
    one must open the terminal and enter hecker mode. 
    Install these dependencies for pip install pyaudio to work.
    It is recommended to use a native package of VS Code for this but 
    FlatSeal may help for the Flatpak version to work.
    
    Ubuntu / Debian / Mint
        sudo apt update

        sudo apt install -y \
        python3-pip \
        python3-venv \
        portaudio19-dev \
        python3-dev \
        ffmpeg
        
    Fedora
        sudo dnf install -y \
        python3-pip \
        python3-devel \
        portaudio-devel \
        ffmpeg
    
    Arch Linux
        sudo pacman -S \
        python-pip \
        portaudio \
        ffmpeg
'''


import google.generativeai as genai
import speech_recognition as sr
import os

# Configure your API Key
genai.configure(api_key="API")

# 1. Define Ramsey's specific persona and rules
ramsey_persona = """
You are Ramsey, an expert PC building assistant and hardware technician. 
Your primary goal is to help users design custom PCs, check part compatibility, suggest budget-friendly upgrades, and troubleshoot hardware issues. 
You should be enthusiastic, knowledgeable, and provide easy-to-understand explanations for both beginners and experts.
If a user asks a question that is NOT related to PC building, computers, or gaming hardware, you must politely decline to answer and steer the conversation back to PC building.
"""

# 2. Initialize the model with the system instruction
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    system_instruction=ramsey_persona
)

# 3. Start the chat
chat = model.start_chat(history=[])

# Initialize the speech recognizer
recognizer = sr.Recognizer()
# A shorter pause threshold makes the "bursts" process faster
recognizer.pause_threshold = 0.8 

# Calibrate background noise once at startup
print("Calibrating microphone...")
with sr.Microphone() as source:
    recognizer.adjust_for_ambient_noise(source, duration=1)

def listen_for_chunk(source):
    """Listens for a quick burst of speech without spamming the console."""
    try:
        audio = recognizer.listen(source, timeout=2, phrase_time_limit=15)
        return recognizer.recognize_google(audio)
    except sr.WaitTimeoutError:
        return None  # You are just pausing/thinking
    except sr.UnknownValueError:
        return None  # It heard a noise but no words
    except sr.RequestError:
        return None

def chat_with_gemini(user_input):
    response = chat.send_message(user_input)
    return response.text

print("\nHI, I'M RAMSEY! (Voice Mode Activated)")
print("Say 'Speech Done' to send your message to Ramsey.")
print("Say 'Quit' or 'Exit' to stop the program.\n")

trigger_phrases = ["speech done", "thank you"]

while True:
    print("🎤 [Mic is ON] Start speaking...")
    full_user_input = ""
    
    # Keep the microphone open continuously while building the sentence
    with sr.Microphone() as source:
        while True:
            chunk = listen_for_chunk(source)
            
            if chunk:
                print(f" > {chunk}")
                full_user_input += chunk + " "
                
                # The trigger word to break the loop and send to AI
                if any(trigger in chunk.lower() for trigger in trigger_phrases):
                    break

    final_prompt = full_user_input.lower()
    
    # Remove trigger phrases from final message
    for trigger in ["speech done", "thank you"]:
        final_prompt = final_prompt.replace(trigger, "")

    final_prompt = final_prompt.strip()
    
    # Check for exit commands
    if final_prompt in ["quit", "exit", "bye", "goodbye"]:
        print("Chatbot Ramsey: Goodbye!")
        break
        
    # Ignore accidental empty prompts
    if not final_prompt or len(final_prompt) < 2:
        continue
        
    # Send to Gemini
    try:
        print("\n🛑 [Mic is OFF] 🤖 Chatbot Ramsey is thinking...")
        ai_response = chat_with_gemini(final_prompt)
        print(f"Chatbot Ramsey: {ai_response}\n")
    except Exception as e:
        print(f"\n[!] An error occurred: {e}\n")
