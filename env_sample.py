def get_env_variable(key):

    env_variable_dict = {
        # Open AI
        "OPENAI_API_KEY" : "sk-proj-",
        # Azure Speech
        "AZURE_SPEECH_KEY" : "",
        "AZURE_SPEECH_REGION" : "", 
    }
    ret_val = env_variable_dict.get(key, None)
    return ret_val