import random

numbers = [random.randint(1, 100) for _ in range(10)]
numbers.sort(reverse=True)

with open('sorted.txt', 'w') as f:
    for num in numbers:
        f.write(f"{num}\n")