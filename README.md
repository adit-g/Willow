# Willow  
An open-sourced virtual assistant (in-progress)
### Project Description
This project has been developed entirely in Python, including the designing and training of the two machine learning models. They are described here: 
 * wake_word_model.tflite - A binary classifier CNN model which takes in a a second segment of audio and determines whether the word "willow" was spoken in the audio.
    * Datasets: I asked all my friends and family to say the word willow 20 times, and I created a dataset using these audio clips for the positive class and background noise/random words I found online for the negative class.
    * Limitations: The positive class currently contains a very limited number of samples, and does not accurately represent a diverse demographic of accents and voices. The model is also sometimes prone to false activations.
* model.tflite - A BERT model for intent classification using natural language processing. It takes in a sentences and returns 1 of 64 possible intents
    * Datasets: Trained using a dataset of voice commands I found online
    * Limitations: The BERT model contains over 110 million parameters, and can sometimes be very slow when running on a resource-constrained Raspberry Pi. This is not a problem on MacOS.
### How to Use Willow:
1. Ensure python and pip are downloaded and fully updated on your Mac machine
2. Clone the repository into a folder locally on your machine
3. Navigate to the repository's folder in the command line/terminal
4. Create a new virtual environment using the following command: "python3 -m venv env"
5. Activate the virtual environment using "source env/bin/activate"
6. Run "pip install -r requirements.txt"
7. Run "python3 test_willow_full.py" and see what willow can do!
DISCLAIMER: The wake word model was trained on a very small dataset of voices(just my friends and I), so there is a high chance that a new voice will not trigger a response from willow
Note: willow has only been tested on MacOS and a raspberry pi 3B+ running Raspbian Bullseye, any other platform or device may or may not support willow
### Demo
https://user-images.githubusercontent.com/118241732/202987819-6b4795a2-137c-4ebd-98f8-d1df959c5c60.mp4

(Sorry for the abysmal video quality, github required the size to be less than 10mb)
### Why I Created Willow:
I created this program to provide my room with a virtual assistant better than Amazon Alexa or Google Home. As of now, it can run 24/7 on my raspberry pi and provide me basic alarm functionality, but I am working on making it much more than that. Coding my own assistant gives me flexibility to implement any skill I could possibly want, whereas with commercially available assistants I am limited to the skills they provide for us. Additionally, certain features on Alexa or Google require the user to pay extra, such as on-demand music streaming, but I wish to make my assistant free for me and any other users who may clone this repository.
