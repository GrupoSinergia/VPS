import ollama

def generate_reply(prompt, model="llama3.2:3b-instruct-q4_k_m"):
    """
    Generate reply optimized for real-time voice conversations.
    Target: < 5 second response time for telephony use.
    """
    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={
            # CRITICAL: Limit response length for voice interaction
            "num_predict": 100,  # Max 100 tokens (~75 words, ~15-20s of speech)

            # Speed optimizations
            "temperature": 0.7,  # Slightly lower = faster, more focused
            "top_k": 20,         # Reduce sampling pool for speed
            "top_p": 0.8,        # Nucleus sampling for faster generation

            # Context optimizations
            "num_ctx": 2048,     # Reduce context window from default 4096
            "num_batch": 512,    # Batch size for prompt processing

            # Performance tuning
            "num_thread": 4,     # Limit threads to prevent context switching
            "repeat_penalty": 1.1,  # Reduce repetition

            # Disable streaming for simplicity (already false in current usage)
        }
    )
    return response['response']
