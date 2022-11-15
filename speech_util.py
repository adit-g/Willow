""" This script includes general methods for text to speech and speech to text
    Not a class so that all files can access methods at any time"""

from gtts import gTTS
from playsound import playsound
import speech_recognition as sr

samplerate = 16000
r = sr.Recognizer()

def calibrate_mic():
    with sr.Microphone(sample_rate=samplerate) as source2:
        print("calibrating... silence please")
        r.adjust_for_ambient_noise(source2, duration=2)
        print("done")

def transcribe():
    with sr.Microphone(sample_rate=samplerate) as source2:
        audio2 = r.listen(source2)
    try:
        text = r.recognize_google(audio2)
    except sr.UnknownValueError:
        text = None
    return text

def speak(sentence):
    tts = gTTS(sentence)
    tts.save('utils/sentence.mp3')

    playsound("utils/sentence.mp3")

def ring_alarm():
    playsound("utils/Google-Duo.mp3", False)



