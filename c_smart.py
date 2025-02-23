import os
import random
from threading import Event
import time
import re
from typing import List
import Levenshtein
from gensim.models import KeyedVectors
from collections import Counter
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# loads french model
models = ['cc.fr.300.vec', 'wiki.fr.vec']
print(f"Loading word model...", end='')
french_model = KeyedVectors.load_word2vec_format(models[0], binary=False, encoding='utf-8', unicode_errors='ignore')
print(f"done!")


class CemantixSmartSolver:
    """
    Class for a "smart" cemantix solver.

    Description:
    The CemantixSmartSolver class uses all the information gained by the random solvers to try to deduce
    the word of the day by appormating the semantic scores thanks to a model.

    Arguments:
    smart_words_file (str): Path to the file to save used words.
    close_words_file (str): Path to the file to save useful words.
    verbose (int): Verbose argument, 0=nothing, 1=success message, 2=every word.
    """

    def __init__(self, smart_words_file="smart_words/smart_words.txt", close_words_file="close_words/close_words_0.txt", verbose: int=1):
        self.smart_words_file = smart_words_file
        self.close_words_file = close_words_file
        self.driver = None
        self.start_time = None
        self.try_count = 0
        self.found_success = False
        self.verbose = verbose
        self._init_files()

    def _init_files(self):
        with open(self.smart_words_file, "w") as file:
            file.write("\n")
        with open(self.close_words_file, "w") as file:
            file.write("\n")
        with open("log.txt", "w") as file:
            file.write("\n")

    def _close_files(self):
        if os.path.exists(self.smart_words_file):
            os.remove(self.smart_words_file)
        if os.path.exists(self.close_words_file):
            os.remove(self.close_words_file)

    # Driver funtions
    def _initialize_driver(self):
        """
        Sets up a Firefox driver
        """
        self.driver = webdriver.Firefox()
        self.driver.maximize_window()

    def _open_cemantix(self):
        """
        """
        url = "https://cemantix.certitudes.org/"
        self.driver.get(url)

    def _close_dialog(self):
        """
        Close the popup dialog
        """
        wait = WebDriverWait(self.driver, 10)
        close_button = wait.until(EC.presence_of_element_located((By.ID, "dialog-close")))
        close_button.click()

    def _get_input_field(self):
        """
        Get the input field
        """
        wait = WebDriverWait(self.driver, 10)
        return wait.until(EC.presence_of_element_located((By.ID, "cemantix-guess")))

    def _check_for_success(self):
        """
        Check if success
        """
        tries = 0
        while tries < 5:
            tries+=1
            #doc can go stale you know how it is
            try:
                success_element = self.driver.find_elements(By.ID, "cemantix-success")
                style = success_element[0].get_attribute("style")
                return style == "opacity: 1; max-height: 100%; margin-bottom: 0.25em; display: block;"
            except:pass
        return False

    def _extract_winning_word(self):
        tries = 0
        while tries < 5:
            tries+=1
            try:
                table = self.driver.find_element(By.ID, "cemantix-guessable")
                tbody = table.find_element(By.ID, "cemantix-guesses")
                rows = tbody.find_elements(By.TAG_NAME, "tr")
                for row in rows:
                    try:
                        word_cell = row.find_element(By.CSS_SELECTOR, "td.word.close")
                        number_cells = row.find_elements(By.CSS_SELECTOR, "td.number.close")
                        if len(number_cells) >= 2:
                            second_number = float(number_cells[1].text)
                        if second_number == 1000 : return word_cell.text
                    except:pass
            except: pass
        return "UNKNOWN" 

    def _extract_close_words(self):
        """
        Extract the close words from driver
        """
        try:
            table = self.driver.find_element(By.ID, "cemantix-guessable")
            tbody = table.find_element(By.ID, "cemantix-guesses")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            close_words = []
            for row in rows:
                if "separator" not in row.get_attribute("class"):
                    try:
                        word_cell = row.find_element(By.CSS_SELECTOR, "td.word.close")
                        number_cell = row.find_element(By.CSS_SELECTOR, "td.number.close")
                        close_words.append((word_cell.text, number_cell.text))
                        if len(close_words) == 100:
                            break
                    except:pass
            return close_words
        except Exception:
            return []

    def _input_word(self, input_field, word: str):
        input_field.clear()
        input_field.send_keys(word)
        input_field.send_keys(Keys.RETURN)

    def _finish_setup(self, quit_event: Event):
        quit_event.set()
        time_end = time.time() - self.start_time
        current_datetime = datetime.now()
        word = self._extract_winning_word()
        self.driver.quit()
        self._close_files()
        if self.verbose > 0 : print(f"Word is \"{word}\", succeded in {'{0:.2f}'.format(time_end)}s at {current_datetime} !")
        return word, time_end

    # txt functions
    def _save_used_words(self, used_words:List[str]):
        """
        Save the words we have used so far into txt file
        """
        with open(self.smart_words_file, 'a', encoding='utf-8') as file:
            for word in used_words:
                file.write(f"{word}\n")

    def _save_close_words(self, close_words:List[str]):
        """
        Save the close words into txt file
        """
        with open(self.close_words_file, 'w', encoding='utf-8') as file:
            #ex: cordialité:23.08
            for word, number in close_words:
                file.write(f"{word}:{number}\n")

    def _load_words(self, close_folder_path:str = "close_words", far_folder_path:str = "far_words") -> tuple[List[str], List[str], List[str], List[str]]:
        """
        Loards close and far words from txt files
        """
        far_words = []
        far_words_dic = {}
        for filename in os.listdir(far_folder_path):
            file_path = os.path.join(far_folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file.readlines():
                        line = line.strip()
                        if ':' in line:
                            word, value = line.split(':')
                            far_words_dic[word] = value
            sorted_far_words = sorted(far_words_dic.items(), key=lambda x: x[1])
            bottom_100_words = sorted_far_words[:100]
            bottom_100_words = bottom_100_words[::-1]
            far_words = [word for word, _ in bottom_100_words]

        # Close Wrods
        sorted_close_words = []
        close_words = []
        top_close_words = []
        for filename in os.listdir(close_folder_path):
            file_path = os.path.join(close_folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    for line in file.readlines():
                        line = line.strip()
                        if ':' in line:
                            word, score = line.split(':')
                            try:
                                score = float(score)
                                sorted_close_words.append((word, score))
                            except ValueError:
                                pass
                            
        sorted_close_words.sort(key=lambda x: x[1], reverse=True)
        output_words = []
        for word, score in sorted_close_words:
            if score == 100.00:
                self._input_word(self._get_input_field(), word)
                close_words = [word]
                return [], close_words, [], []
            elif score >= 51.90:    # this is pretty close
                close_words.append(word)
                output_words.append(word)
                output_words.extend(self._get_close_word(word, top_n=min(self.try_count,20)))  # this is a leverstein distance closeness not semantic so don't add it to close_words
            else:
                close_words.append(word)
        if len(sorted_close_words)>0:
            top_value = sorted_close_words[0][1]
            top_close_words.append(sorted_close_words[0])
            for word, score in sorted_close_words[1:]:
                if abs(score - top_value) <= 10:
                    top_close_words.append(word)
                else:
                    break
        return far_words, close_words, top_close_words, output_words

    # Guess functions
    def _generate_semantic_guesses(self, close_folder_path: str = "close_words", far_folder_path: str = "far_words") -> List[str]:
        """
        Generate semantic guesses based on the scores of words from close and far word lists.
        """

        # Load and process words from txt files
        far_words, close_words, top_close_words, output_words = self._load_words(close_folder_path, far_folder_path)
        
        if len(far_words)==0 and len(close_words)==1:
            return close_words

        # Generate output words based on close and far words
        output_words.extend(self._generate_output_words(close_words, top_close_words, far_words))
        
        # Filter the output words based on previously saved  in the smart words files
        filtered_output = self._filter_smart_words(output_words)
        
        return filtered_output

    def _log(self, data, model=""):
        with open("log.txt", mode='a', encoding='utf-8') as file:
            file.write(f"{self.try_count},{model}: {data}\n")

    def _generate_output_words(self, close_words: List[str], top_close_words: List[str], far_words: List[str]) -> List[str]:
        """
        Generate output words based on close and far words using a french words vec model
        """
        if len(far_words) == 0:
            far_words = None
        if len(close_words) == 0:
            return []
        elif len(close_words) == 1:
            output_words = close_words
            return output_words
        output_words = []
        max_word_count = min(self.try_count,50)

        # Basic similar words
        _similar_words =[]
        _similar_words.extend(
            self._get_similar_words_array_input(top_close_words, far_words, top_n=max_word_count))
        _similar_words.extend(
            self._get_similar_words_array_input(top_close_words, top_n=max_word_count))
        self._log(_similar_words, "Basic")

        # Randomness
        _random_words = []
        _random_words.extend(
            self._get_similar_words_array_input(
                self._random_array_crop(close_words), top_n=max_word_count))
        _random_words.extend(
            self._get_similar_words_array_input(
                self._random_array_crop(close_words), self._random_array_crop(far_words), top_n=max_word_count))
        _random_words.extend(
            self._get_similar_words_array_input(
                self._random_array_crop(top_close_words), top_n=max_word_count))
        self._log(_random_words, "Random")

        # Best matches
        _best_words = []
        _best_words.extend(
            self._get_similar_words_singular_input(close_words[0], far_words, top_n=max_word_count))
        _best_words.extend(
            self._get_similar_words_singular_input(close_words[0], top_n=max_word_count))
        _best_words.extend(
            self._get_similar_words_array_input(close_words[:5], far_words, top_n=max_word_count))
        _best_words.extend(
            self._get_similar_words_array_input(close_words[:5], top_n=max_word_count))
        self._log(_best_words, "Best")

        output_words.extend(_similar_words)
        output_words.extend(_random_words)
        output_words.extend(_best_words)
        return output_words

    def _filter_smart_words(self, output_words: List[str]) -> List[str]:
        """
        Filter out words already in the smart words file
        """
        with open('smart_words/smart_words.txt', 'r', encoding='utf-8') as file:
            smart_words = set(word.strip().lower() for word in file)

        return [word for word in output_words if word.strip().lower() not in smart_words]

    def _random_array_crop(self, arr1: List[any], retention_probability: float = 0.75) -> List[any]:
        """
        Randomly crops the list of words
        """
        if arr1 is None or len(arr1) == 0:
            return []

        def should_keep(index, array_length, retention_probability):
            weight = (array_length - index) / array_length  # Linear decay of the weight
            return random.random() < weight * retention_probability

        cropped_array = [item for idx, item in enumerate(arr1) if 
                         should_keep(idx, len(arr1), retention_probability)]
        return cropped_array

    #  Model functions, semantic -> similar, Levenshtein -> close
    def _get_similar_words_singular_input(self, input_word: str, negative_words: List[str] = None, top_n: int = 100) -> List[str]:
        """
        Get similar words for a single input word using a semantic model
        """
        if input_word is None or input_word not in french_model:
            return []

        try:
            similar_words = [word for word, _ in french_model.most_similar(positive=[input_word], negative=negative_words, topn=top_n)]
            return similar_words
        except KeyError as e:
            missing_word = str(e).split("'")[1]
            if input_word == missing_word: 
                return []
            if negative_words:
                negative_words = [word for word in negative_words if word != missing_word]
            return []

    def _get_similar_words_array_input(self, input_words: List[str], negative_words: List[str] = None, top_n: int = 100) -> List[str]:
        """
        Get similar words for an array of input words using a semantic model
        """
        if input_words is None or len(input_words) == 0:
            return []

        input_words_temp = list(input_words)
        for word in input_words_temp:
            if word not in french_model:
                input_words.remove(word)

        if(len(input_words)<1):
            return []
        
        while True:
            try:
                similar_words = [word for word, _ in french_model.most_similar(positive=input_words, negative=negative_words, topn=top_n)]
                break
            except KeyError as e: # Handles 'not in vocabulary' error, shouldn't happen byt you never know
                missing_word = str(e).split("'")[1]
                input_words = [word for word in input_words if word != missing_word]
                if negative_words: negative_words = [word for word in negative_words if word != missing_word]

        return similar_words

    def _get_close_words(self, over_51_words: List[str], sorted_words: List[str] = None, max_distance: int = 2, top_n: int = 100) -> List[str]:
        """
        Get close words based on Levenshtein distance, for an array input
        """
        if len(over_51_words) == 1:
            return self._get_close_word(over_51_words, sorted_words, max_distance, top_n)
        elif len(over_51_words) < 1:
            return []
        if not sorted_words:
            with open('liste_francais_maculins_utf8.txt', 'r', encoding='utf-8') as f:
                sorted_words = [line.strip() for line in f.readlines()]
        close_words = []
        for word in over_51_words:
            try:
                mid_index = sorted_words.index(word)
            except ValueError: continue  # skip
            low_index = max(mid_index - 10, 0)
            for i in range(20):
                if self._levenshtein_distance(word, sorted_words[low_index + i]) <= max_distance:
                    close_words.append(sorted_words[low_index + i])

        return close_words

    def _get_close_word(self, over_51_word: List[str], sorted_words: List[str] = None, max_distance: int = 2, top_n: int = 100) -> List[str]:
        """
        Get close words based on Levenshtein distance, for an singular input
        """
        if len(over_51_word) > 1:
            return self._get_close_words(over_51_word, sorted_words, max_distance, top_n)
        if not sorted_words:
            with open('liste_francais_maculins_utf8.txt', 'r', encoding='utf-8') as f:
                sorted_words = [line.strip() for line in f.readlines()]
        close_words = []
        try:mid_index = sorted_words.index(over_51_word)
        except ValueError: return []    # this error is unliekely 
        low_index = max(mid_index - 10, 0)
        for i in range(top_n):
            if self._levenshtein_distance(over_51_word, sorted_words[low_index+i]) <= max_distance:
                close_words.append(sorted_words[low_index+i])

        return close_words

    def _levenshtein_distance(self, word1: str, word2: str) -> int:
        """
        Calculate Levenshtein distance between two words
        """
        return Levenshtein.distance(word1, word2)


    def run(self, stop_event: Event, quit_event: Event, result_array = []) -> tuple[str | float]:
        """
        """
        self.start_time = time.time()
        self._initialize_driver()
        self._open_cemantix()
        self._close_dialog()
        input_field = self._get_input_field()
        used_words = []

        print(f"", end="")
        while True:
            words = []
            self.try_count+=1
            while len(words) < 1:
                words = self._generate_semantic_guesses()
                pattern = re.compile(r"^[a-zA-ZÀ-ÿéèçàêôîïüöàÀ-ÿ\s\-]+$")
                words = [word for word in words if pattern.match(word)]
                time.sleep(0.1)

            while len(words) >= 1:
                word = words.pop(0)
                self._input_word(input_field=input_field, word=word)
                if self.verbose > 1 :print(f"{word}                           ", end="\r")
                used_words.append(word)
                time.sleep(0.1)
                if self._check_for_success():
                    self.found_success = True
                    break
                if stop_event.is_set():
                    break

            if self.found_success:
                time.sleep(5)
                stop_event.set()
                break
                    
            self._save_used_words(used_words)
            used_words = []

            close_words = self._extract_close_words()
            self._save_close_words(close_words)

        self._input_word(input_field=input_field, word="lave")
        results = self._finish_setup(quit_event=quit_event)
        result_array.extend(results)    # this is a mutable object passed in the arguments to be able to return the results even when we use a thread
        return results