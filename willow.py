""" This script keeps the natural language processing model loaded 
    so that any file can use it. Contains a method to predict an intent
    using a user utterance"""

import tensorflow as tf
import pickle
import numpy as np

with open('utils/tokenizer.pkl','rb') as file:
    tokenizer = pickle.load(file)

interpreter = tf.lite.Interpreter(model_path="bert/model.tflite")
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()
 
def find_intent(utr):
    tokens = ["[CLS]"] + tokenizer.tokenize(utr) + ["[SEP]"]

    token_ids = []
    token_ids.append(list(tokenizer.convert_tokens_to_ids(tokens)))
    token_ids[0] += [0]*(30-len(token_ids[0]))
    token_ids = np.array(list(token_ids), dtype=np.int32)

    interpreter.set_tensor(input_details[0]['index'], token_ids)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])

    highest_probability = np.amax(output_data)
    index = np.where(output_data == highest_probability)[1][0]

    return (index, highest_probability)

