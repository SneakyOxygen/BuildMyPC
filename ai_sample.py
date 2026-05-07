# do this pip install --upgrade google-generativeai
# and this pip install google.generativeai
# and this pip install SpeechRecognition
# and this pip install pipwin
# then this pip install pyaudio
# and this pip install pyttsx3 (text to speech)
# next, go to aistudio.google.com
# find "Get API key" located at the bottom left
# then copy your API key
# paste it in the api_key=

'''
    To install Pyaudio in Linux di
'''


import google.generativeai as genai
import speech_recognition as sr
import os

# Configure your API Key
genai.configure(api_key="API")

# Initialize the model and chat
model = genai.GenerativeModel("gemini-2.5-flash")
chat = model.start_chat(history=[])

# Initialize the speech recognizer
recognizer = sr.Recognizer()
recognizer.pause_threshold = 3.0

def listen_to_mic():
    """Turns on the mic, listens until you stop speaking, and returns the text."""
    with sr.Microphone() as source:
        print("\n🎤 [Mic is ON] Listening... (speak now)")
        
        # Adjust for ambient background noise to improve accuracy
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        
        try:
            # Listens until it detects a pause in your speech
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            print("🛑 [Mic is OFF] Processing your speech...")
            
            # Send the audio to Google's free speech-to-text service
            text = recognizer.recognize_google(audio)
            return text
            
        except sr.WaitTimeoutError:
            # Triggered if you don't say anything
            return None
        except sr.UnknownValueError:
            print("[!] Sorry, I couldn't understand the audio.")
            return None
        except sr.RequestError as e:
            print(f"[!] Could not request results; {e}")
            return None

def chat_with_gemini(user_input):
    response = chat.send_message(user_input)
    return response.text

print("HI, I'M NOVA! (Voice Mode Activated)\n")
print("Just say 'quit', 'exit', or 'bye' to stop.")

while True:
    # 1. Turn on mic and wait for user to speak
    user_input = listen_to_mic()
    
    # If the mic didn't catch anything, restart the loop and listen again
    if not user_input:
        continue
        
    print(f"You said: \"{user_input}\"")
    
    # 2. Check for exit commands
    if user_input.lower() in ["quit", "exit", "bye", "goodbye"]:
        print("Chatbot Nova: Goodbye!")
        break
        
    # 3. Send to Gemini (Mic is currently OFF)
    try:
        print("🤖 Chatbot Nova is thinking...")
        ai_response = chat_with_gemini(user_input)
        print(f"Chatbot Nova: {ai_response}")
        # Loop restarts, mic turns back ON
    except Exception as e:
        print(f"\n[!] An error occurred: {e}\n")