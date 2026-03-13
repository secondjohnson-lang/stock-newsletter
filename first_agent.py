import os
import requests

api_key = os.getenv("OPENROUTER_API_KEY")

messages = [
    {
        "role": "system",
        "content": """You are Alex, a friendly and professional Tier 1 support agent 
        for a SaaS company. Your job is to help customers troubleshoot issues with 
        their account and application access.
        
        Guidelines:
        - Always greet the customer warmly
        - Ask clarifying questions before jumping to solutions
        - Keep responses concise and easy to follow
        - Use numbered steps when giving instructions
        - If an issue is beyond Tier 1 support, say: 
          'I'm going to escalate this to our specialist team who can better assist you'
        - Never make up information you don't know
        - End every response by asking if there is anything else you can help with"""
    }
]

print("=" * 50)
print("Welcome to Support! I'm Alex, how can I help?")
print("=" * 50)

while True:
    user_input = input("Customer: ")
    
    if user_input.lower() == "quit":
        print("Alex: Thank you for contacting support. Have a great day!")
        break
    
    messages.append({"role": "user", "content": user_input})
    
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}"
        },
        json={
            "model": "stepfun/step-3.5-flash:free",
            "messages": messages
        }
    )
    
    data = response.json()
    reply = data["choices"][0]["message"]["content"]
    
    messages.append({"role": "assistant", "content": reply})
    
    print(f"\nAlex: {reply}\n")
    print("-" * 50)