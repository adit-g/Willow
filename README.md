# willow

## Project Description

I created this program to provide my room with a virtual assistant better than Amazon Alexa or Google Home. As of now, it can run 24/7 on my raspberry pi and provide me basic alarm functionality, but I am working on making it much more than that. Coding my own assistant gives me flexibility to implement any skill I could possibly want on it, whereas with commercially available assistants I am limited to their skillset. Additionally, certain features on Alexa or Google require the user to pay extra, such as on-demand music streaming, but I wish to make my assistant free for me and any other users who may clone this repository.


how to run willow:

1. clone the repository into a folder locally
2. navigate to that folder in the command line/terminal
3. create a new virtual environment using the following command: "python3 -m venv env"
4. activate the virtual environment using "source env/bin/activate"
5. run "pip install -r requirements.txt"
6. run "python3 test_willow_full.py" and see what willow can do!


Note: willow has only been tested on MacOS and a raspberry pi 3B+ running Raspbian Bullseye, any other platform or device may or may not support willow
