import lmstudio as lms  

#lms.configure_default_client(api_token="sk-lm-ITCeAy2V:QiOWmkGIkKUjcgAYFmbU")

model =lms.llm("google/gemma-4-e4b")
result = model.respond("What is the meaning of life?")
print(result)