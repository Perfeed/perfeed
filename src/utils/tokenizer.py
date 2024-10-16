import tiktoken
from pandas import Timestamp


def count_tokens(text, model="gpt-4o"):
    # Load the appropriate encoding for the model
    encoding = tiktoken.encoding_for_model(model)
    # Encode the text to get tokens
    tokens = encoding.encode(text)
    # Return the number of tokens
    return len(tokens)
