import multiprocessing
import time

from task import downloadVideo

PROCESSES = multiprocessing.cpu_count() - 1
NUMBER_OF_TASKS = 20







def process_tasks(task_queue):
    while not task_queue.empty():
        book = task_queue.get()
        print(book)
        downloadVideo(book)
    return True


def add_tasks(task_queue, number_of_tasks):
    for num in range(number_of_tasks):
        task_queue.put("s")
    return task_queue


def run():
    empty_task_queue = multiprocessing.Queue()
    full_task_queue = add_tasks(empty_task_queue, NUMBER_OF_TASKS)
    processes = []
    print(f"Running with {PROCESSES} processes!")
    start = time.time()
    for n in range(PROCESSES):
        p = multiprocessing.Process(target=process_tasks, args=(full_task_queue,))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()
    print(f"Time taken = {time.time() - start:.10f}")


if __name__ == "__main__":
    run()