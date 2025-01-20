import threading
from c_random import CemantixRandomSolver
from c_smart import CemantixSmartSolver # loading the FastText French model takes a while (~200s), consider runing this with an anaconda gpu venv

def main(thread_count = 3, verbose = 2):
    if thread_count < 1: thread_count = 1
    results = []
    stop_event = threading.Event()
    quit_event = threading.Event()
    threads = []
    for i in range(thread_count):
        solver = CemantixRandomSolver(instance=i+1, lang_usable_words="cemantix_words_rough.txt")
        thread = threading.Thread(target=solver.run, args=(stop_event, quit_event,))
        threads.append(thread)
        thread.start()
    script = CemantixSmartSolver(verbose=verbose)
    smart_thread = threading.Thread(target=script.run, args=(stop_event, quit_event, results,))
    threads.append(smart_thread)
    smart_thread.start()
    for thread in threads:
        thread.join()
    return results

if __name__ == "__main__":
    main(1,2)