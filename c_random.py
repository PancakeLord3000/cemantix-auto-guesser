import os
import random
from threading import Event
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
       
class CemantixRandomSolver:
    """
    Class for a random cemantix solver.

    Description:
    The CemantixRandomSolver class manages the random insertion of words into a cemantix and the
    saving of the most useful words found.

    Arguments:
    instance (int): Instance number, determines where the class saves useful words.
    lang_usable_words (str): Path to the file containing the words to insert in cemantix.
    """

    def __init__(self, instance:int, lang_usable_words:str = "liste_francais_maculins_utf8.txt"):
        if instance < 1: instance = 1
        self.instance = instance
        self.lang_usable_words = lang_usable_words
        self.close_words_txt = f"close_words/close_words_{self.instance}.txt"
        self.far_words_txt = f"far_words/far_words_{self.instance}.txt"
        self.driver = None
        self.words = self._load_words()
        self.found_success = False
        self._init_files()

    def _init_files(self):
        with open(self.close_words_txt, "w") as file:
            file.write("\n")
        with open(self.far_words_txt, "w") as file:
            file.write("\n")

    def _close_files(self):
        if os.path.exists(self.close_words_txt):
            os.remove(self.close_words_txt)
        if os.path.exists(self.far_words_txt):
            os.remove(self.far_words_txt)

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
        time.sleep(0.5)  # precaution
        url = "https://cemantix.certitudes.org/"
        self.driver.get(url)

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

    def _extract_best_and_worst_words(self,close_size: int = 100, far_size: int = 100):
        """
        Extract the close and far words from driver
        """
        close_words = []
        far_words = []
        try:
            table = self.driver.find_element(By.ID, "cemantix-guessable")
            tbody = table.find_element(By.ID, "cemantix-guesses")
            rows = tbody.find_elements(By.TAG_NAME, "tr")

            for row in rows:
                # if "separator" not in row.get_attribute("class"):
                self._process_row_for_words(row, close_words, far_words)
                if len(close_words) >= close_size and len(far_words) >= far_size:
                    break

            return close_words, far_words

        except Exception as e:
            print(f"Error in getting best/worst words: {e}")
            return close_words, far_words

    def _process_row_for_words(self, row, close_words, far_words):
        """
        Extract close or far words from a row of <cemantix-guesses><tr>
        """
        if len(close_words) < 100:
            try:
                word_cell = row.find_element(By.CSS_SELECTOR, "td.word.close")
                number_cell = row.find_element(By.CSS_SELECTOR, "td.number.close")
                close_words.append((word_cell.text, number_cell.text))
            except:
                pass

        if len(far_words) < 100:
            try:
                number_cells = row.find_elements(By.CSS_SELECTOR, "td.number")
                if len(number_cells) >= 2:
                    second_number = float(number_cells[1].text)
                    if second_number < 0 :
                        word_cell = row.find_element(By.CSS_SELECTOR, "td.word")
                        far_words.append((word_cell.text, second_number))
            except:
                pass

    def _succeeding(self, quit_event: Event):
        """
        """
        def _empty_files():
            for filename in os.listdir("far_words"):
                file_path = os.path.join("far_words", filename)
                with open(file_path, "w") as file:
                    file.write("\n")
            for filename in os.listdir("close_words"):
                file_path = os.path.join("close_words", filename)
                with open(file_path, "w") as file:
                    file.write("\n")
                
        while True:
            _empty_files()
            try:
                # the "winning" word can be the last, in that case it's not aprt of the cemantix-guesses array, so we input a random word to move it there
                input_field = self._get_input_field()
                input_field.clear()
                input_field.send_keys("lave")
                input_field.send_keys(Keys.RETURN)
                close_words, _ = self._extract_best_and_worst_words(3,0)
                self._write_to_file(self.close_words_txt, close_words)
            except Exception as e:
                print(f"Error while suffering from success: {e}")
            time.sleep(5)
            if quit_event.is_set():
                break

    # txt functions
    def _load_words(self):
        """
        Loads close and far words from txt files
        """
        with open(self.lang_usable_words, 'r', encoding='utf-8') as file:
            words = file.read().splitlines()
        random.shuffle(words)
        return words

    def _write_to_file(self, file_path, data):
        """
        Save the close words into txt file
        """
        with open(file_path, 'w', encoding='utf-8') as file:
            for word, number in data:
                file.write(f"{word}:{number}\n")

    def _get_next_word(self):
        """
        """
        try:
            return self.words.pop(0)
        except IndexError:
            if not self.words:
                self.words = self._load_words()
                return self.words.pop(0)
            return None

    def _save_words(self):
        """
        """
        close_words, far_words = self._extract_best_and_worst_words()
        close_words_write = list(close_words)
        far_words_write = list(far_words)

        self._write_to_file(self.close_words_txt, close_words_write)
        self._write_to_file(self.far_words_txt, far_words_write)


    def run(self, stop_event: Event, quit_event: Event):
        """
        """
        self._initialize_driver()
        self._open_cemantix()
        input_field = self._get_input_field()
        
        try_count = 0

        while True:
            word = self._get_next_word()
            if not word:
                break

            time.sleep(0.05)
            input_field.clear()
            input_field.send_keys(word)
            input_field.send_keys(Keys.RETURN)

            try_count += 1

            if try_count % 100 == 0:
                self._save_words()
                self.found_success = self._check_for_success()

            if self.found_success:
                stop_event.set()
                self._succeeding(quit_event)

            if stop_event.is_set():
                break

        while True:
            if quit_event.is_set():
                self.driver.quit()
                self._close_files()
                return
            time.sleep(1)
