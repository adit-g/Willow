"""Runs the entire willow program"""

from speech_util import calibrate_mic, transcribe, speak, ring_alarm
from wake_word_engine import WakeWordEngine
from willow import find_intent
from intent_handler import IntentHandler
import pickle

print('[INFO] modules imported')

calibrate_mic()

wwe = WakeWordEngine()
handler = IntentHandler()

random = 8
with open('utils/classes.pkl','rb') as file:
    classes = pickle.load(file)

# currently willow runs for 8 commands and then exits the program
# this can be changed by changing the the variable 'random' or 
# removing that variable altogether and running an infinite loop
for x in range(random):
    wwe.stream_until_willow()

    if handler.check_for_alarm():
        ring_alarm()
        continue

    print('speak: ')  
    utr = transcribe()

    if utr:
        utr = utr.lower()
    else:
        continue

    print('in:', utr)
    result = handler.handle_special_intents(utr)
    if result[0]:
        speak(result[1])
        continue

    model_result = find_intent(utr)
    print('intent:', classes[model_result[0]], 'confidence:', model_result[1], model_result[0])
    handler.handle_regular_intent(utr, model_result[0])

speak('program terminated successfully')
