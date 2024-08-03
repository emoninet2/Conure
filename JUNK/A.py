import time


def print_numbers():
    for number in range(1, 100):
        print(number)
        time.sleep(1)


if __name__ == "__main__":
    print_numbers()
