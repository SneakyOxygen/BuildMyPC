# do this pip install --upgrade google-generativeai
# and this pip install google.generativeai
# next, go to aistudio.google.com
# find "Get API key" located at the bottom left
# then copy your API key
# paste it in the api_key=
# 
import google.generativeai as genai
import os

# Best practice: Retrieve the key from your system's environment variables
# For now, put your NEW API key here if you are just testing locally
genai.configure(api_key="INSERT_YOUR_API_HERE")

print("HI, I'M NOVA!\n")

# Initialize the model once, outside the loop. 
# gemini-1.5-flash is currently the best choice for fast, general text tasks.
model = genai.GenerativeModel("gemini-2.5-flash")

# Using start_chat() instead of generate_content() allows the bot to remember context
chat = model.start_chat(history=[])

def chat_with_gemini(user_input):
    # send_message automatically appends the user input and model response to the history
    response = chat.send_message(user_input)
    return response.text

while True:
    user_input = input("You: ")
    
    if user_input.lower() in ["quit", "exit", "bye"]:
        print("Chatbot Nova: Goodbye!")
        break
        
    try:
        print("Chatbot Nova:", chat_with_gemini(user_input))
    except Exception as e:
        print(f"\n[!] An error occurred: {e}\n")