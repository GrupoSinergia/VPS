import ollama

def generate_reply(prompt, model="llama3.2:3b-instruct-q4_k_m"):
    response = ollama.generate(model=model, prompt=prompt)
    return response['response']
