from datetime import datetime
import numpy as np
import tensorflow as tf
import python_speech_features
import sounddevice as sd
import pickle
import librosa
from numpy.fft import rfft, rfftfreq, irfft

class WakeWordEngine:
    """ Willow's wake word engine, uses a tensorflow lite model to determine 
        whether audio contains the word willow"""
        
    def __init__(self):
        """Executed immediately after class is initialized"""
        # Parameters
        self.word_threshold = 0.50
        self.rec_duration = 0.5
        self.window_stride = 0.5
        self.samplerate = 16000
        self.resample_rate = 8000
        self.num_channels = 1
        self.num_mfcc = 16
        self.model_path = 'models/wake_word_model_3.tflite'
        self.listen = False
        
        # Sliding window
        self.window = np.zeros(int(self.rec_duration * self.resample_rate) * 2)

        # Load model (using tf lite interpreter)
        self.interpreter = tf.lite.Interpreter(self.model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

    def stream_until_willow(self):
        """Pauses program until the word willow is detected from the user or an alarm is going off"""

        #load alarm list
        with open('things/alarms.pkl', 'rb') as f:
            als : list = pickle.load(f)
        al_list_is_empty = len(als) == 0
        alarm_going_off = False

        print()
        print('Say Willow...')

        #audio stream to detect willow        
        with sd.InputStream(channels=self.num_channels,
                        samplerate=self.samplerate,
                        blocksize=int(self.samplerate * self.rec_duration),
                        callback=self.sd_callback):
            while not self.listen and not alarm_going_off:
                if not al_list_is_empty:
                    alarm_going_off = als[0][0] <= datetime.now()

        if alarm_going_off:
            print('ALARM GOING OFF brrrrrrrrrrr')
        self.listen = False
        self.window = np.zeros(int(self.rec_duration * self.resample_rate) * 2)

    def jankiest(self, audio):
        """audio transformation to remove white noise"""
        n = len(audio)
        yf = rfft(audio)
        xf = rfftfreq(n, 1/n)
        indices = xf > 200
        yf_clean = indices * yf
        return irfft(yf_clean)

    def predict_willow(self, raw_audio, rate):
        """use wake_word_model to guess whether given audio clip contains the word willow"""
        mfccs = python_speech_features.base.mfcc(raw_audio, 
                                            samplerate=rate,
                                            winlen=0.256,
                                            winstep=0.050,
                                            numcep=self.num_mfcc,
                                            nfilt=26,
                                            nfft=2048,
                                            preemph=0.0,
                                            ceplifter=0,
                                            appendEnergy=False,
                                            winfunc=np.hanning)
        mfccs = mfccs.transpose()

        # Make prediction from model
        in_tensor = np.float32(mfccs.reshape(1, mfccs.shape[0], mfccs.shape[1], 1))
        self.interpreter.set_tensor(self.input_details[0]['index'], in_tensor)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        return output_data[0][0]
    
    # This gets called every 0.5 seconds
    def sd_callback(self, rec, frames, time, status):
        """Callback method for the input stream"""

        # Notify if errors
        if status:
            print('Error:', status)

        # Remove 2nd dimension from recording sample
        rec = np.squeeze(rec)

        # Resample
        rec = librosa.resample(rec, orig_sr=self.samplerate, target_sr=self.resample_rate, res_type="linear")
        
        # Save recording onto sliding window
        self.window[:len(self.window)//2] = self.window[len(self.window)//2:]
        self.window[len(self.window)//2:] = rec
        
        # Perform audio transformation
        thing = self.jankiest(self.window)

        val = self.predict_willow(thing, self.resample_rate)

        if val > self.word_threshold:
            self.listen = True
        print(val)

