# cemantix-auto-guesser
This script will use an automated browser to get the Cemantix word of the day. The main file gives a usage example.

The code uses a bunch of random scripts to get score of a lot of words. A single smart thread uses the scores of the random words and a french model to approximate the best words to guess according to the semantic proximity.
This setup only supports the use of a single smart script.
It is recommended to run this code on a venv that uses a gpu to load the model faster.

This git does not contain the .vec file for the french text model. That file needs to be downloded and also configured in the c_smart file. The guessable words are found in "cemantix_words_rough.txt", this file was made automatically to only include the words that can be guesses in cemantix, thus it's not perfect.