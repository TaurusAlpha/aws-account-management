from random import randint

from dotenv import load_dotenv

load_dotenv()

print("Hello World!")

from core import utils


def main():
    it_list = iter([1, 2, 3, 4])
    a = next(it_list)
    print(a)
    b = next(it_list)
    print(b)
   

if __name__ == "__main__":
    main()
