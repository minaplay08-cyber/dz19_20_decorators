# Лабораторная работа 19-20. Декораторы — @timer и @cache

import time
from functools import wraps
import os

# ====== Часть 1: Декоратор @timer ======

print("=== ЧАСТЬ 1: @timer ===\n")

# 1.1. Простой таймер
def timer(func):
    """Замеряет время выполнения функции"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"Функция '{func.__name__}' выполнилась за {end - start:.4f} сек")
        return result
    return wrapper

@timer
def sum_large():
    s = 0
    for i in range(1, 1_000_001):
        s += i
    return s

@timer
def factorial_10():
    r = 1
    for i in range(2, 11):
        r *= i
    return r

@timer
def sort_list():
    import random
    lst = [random.randint(0, 10000) for _ in range(10000)]
    lst.sort()
    return lst[:5]

print("Результаты:")
print(f"  sum_large: {sum_large()}")
print(f"  factorial_10: {factorial_10()}")
print(f"  sort_list: {sort_list()}")

# Если функция ничего не возвращает — декоратор просто не вернёт результат
# (вернёт None), но время всё равно замерит и напечатает

# 1.2. Улучшенный таймер
def timer_precise(unit="auto"):
    """Декоратор с выбором единиц измерения"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            elapsed = end - start

            if unit == "ms" or (unit == "auto" and elapsed < 0.001):
                elapsed_display = elapsed * 1000
                unit_name = "мс"
            elif unit == "us" or (unit == "auto" and elapsed < 0.1):
                elapsed_display = elapsed * 1_000_000
                unit_name = "мкс"
            else:
                elapsed_display = elapsed
                unit_name = "с"

            print(f"[TIMER] {func.__name__}: {elapsed_display:.2f} {unit_name}")
            return result
        return wrapper
    return decorator

# perf_counter() точнее чем time() — процессорный таймер для коротких интервалов

# Сохраняем замеры в список
def timer_stats(func):
    stats = {"calls": 0, "total_time": 0.0, "times": []}
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        stats["calls"] += 1
        stats["total_time"] += elapsed
        stats["times"].append(elapsed)
        print(f"[TIMER] {func.__name__}: {elapsed:.6f} сек (вызов #{stats['calls']})")
        return result
    wrapper.get_stats = lambda: stats
    wrapper.clear_stats = lambda: stats.update({"calls": 0, "total_time": 0.0, "times": []})
    return wrapper

@timer_stats
def test_func():
    time.sleep(0.1)

test_func()
test_func()
print(f"Статистика: {test_func.get_stats()}")

print()

# ====== Часть 2: Декоратор @cache ======

print("=== ЧАСТЬ 2: @cache ===\n")

# 2.1. Простой кэш
def cache_simple(func):
    cache = {}
    def wrapper(arg):
        if arg in cache:
            print(f"  Кэш: берём результат для {arg} из памяти")
            return cache[arg]
        print(f"  Первый вызов: вычисляем результат для {arg}")
        result = func(arg)
        cache[arg] = result
        return result
    return wrapper

@cache_simple
def factorial(n):
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r

print("Факториал:")
print(f"  factorial(5) = {factorial(5)}")
print(f"  factorial(5) = {factorial(5)}")
print(f"  factorial(7) = {factorial(7)}")
print(f"  factorial(5) = {factorial(5)}")

@cache_simple
def fib_rec(n):
    if n <= 1:
        return n
    return fib_rec(n - 1) + fib_rec(n - 2)

print(f"\nfib_rec(10) = {fib_rec(10)}")

# Для 2 аргументов ключом будет кортеж (arg1, arg2)

# 2.2. Универсальный кэш
def cache_universal(func):
    cache = {}
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in cache:
            print(f"  Кэш: {func.__name__}{args} из памяти")
            return cache[key]
        print(f"  Первый вызов: {func.__name__}{args}")
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    return wrapper

@cache_universal
def power(a, b):
    print(f"    (вычисляю {a}^{b})")
    return a ** b

print("\nУниверсальный кэш:")
print(f"  power(2, 10) = {power(2, 10)}")
print(f"  power(2, 10) = {power(2, 10)}")
print(f"  power(3, 4) = {power(3, 4)}")

# Ключ кортеж (args, kwargs) чтобы любое кол-во аргументов хранить
# tuple(sorted(kwargs.items())) упорядочивает kwargs чтобы {"a":1,"b":2} и {"b":2,"a":1} совпадали

# Кэш с ограничением размера
def cache_limited(maxsize=100):
    def decorator(func):
        cache = {}
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            if key in cache:
                print(f"  Кэш: {func.__name__}{args}")
                return cache[key]
            print(f"  Вычисляю: {func.__name__}{args}")
            result = func(*args, **kwargs)
            if len(cache) >= maxsize:
                oldest = next(iter(cache))
                del cache[oldest]
            cache[key] = result
            return result
        wrapper.cache_clear = lambda: cache.clear()
        return wrapper
    return decorator

# 2.3. Кэш с TTL
def cache_ttl(seconds):
    def decorator(func):
        cache = {}
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in cache:
                result, created = cache[key]
                if now - created < seconds:
                    print(f"  Кэш (ещё свежий): {func.__name__}{args}")
                    return result
                else:
                    print(f"  Кэш устарел: {func.__name__}{args}")
            print(f"  Вычисляю: {func.__name__}{args}")
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator

@cache_ttl(5)
def get_time():
    return time.time()

print("\nTTL кэш (живёт 5 сек):")
t1 = get_time()
t2 = get_time()
time.sleep(3)
t3 = get_time()
time.sleep(3)
t4 = get_time()
print(f"  {t1:.2f}, {t2:.2f}, {t3:.2f}, {t4:.2f}")

print()

# ====== Часть 3: Комбинирование декораторов ======

print("=== ЧАСТЬ 3: Комбинирование ===\n")

def timer_func(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"  [TIMER] {func.__name__}: {time.perf_counter() - start:.6f} сек")
        return result
    return wrapper

def cache_func(func):
    store = {}
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = (args, tuple(sorted(kwargs.items())))
        if key in store:
            print(f"  Кэш для {func.__name__}{args}")
            return store[key]
        result = func(*args, **kwargs)
        store[key] = result
        return result
    return wrapper

@timer_func
@cache_func
def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

print("Сначала @timer, потом @cache:")
print(f"  fib(35) = {fib(35)}")
print(f"  fib(35) = {fib(35)}")

# Если поменять местами (@cache @timer), кэш будет снаружи
# и таймер будет только при промахе кэша

def logger(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"  LOG: вызываю {func.__name__}(args={args}, kwargs={kwargs})")
        result = func(*args, **kwargs)
        print(f"  LOG: {func.__name__} вернул {result}")
        return result
    return wrapper

@timer_func
@logger
def hello(name):
    return f"Привет, {name}!"

print("\nКомбо с @logger:")
hello("Анна")

print()

# ====== Часть 4: Творческое задание ======

print("=== ЧАСТЬ 4: Свой декоратор ===\n")

# @retry — повторяет если упала с ошибкой
def retry(attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"  Ошибка (попытка {i+1}/{attempts}): {e}")
                    if i < attempts - 1:
                        time.sleep(delay)
            raise
        return wrapper
    return decorator

@retry(attempts=3, delay=0.5)
def unstable():
    import random
    if random.random() < 0.7:
        raise ConnectionError("Сеть упала")
    return "Успех!"

import random
print("Тест @retry (может упасть 3 раза):")
try:
    print(f"  {unstable()}")
except:
    print("  Все попытки исчерпаны")

print()

# ====== Часть 5: Задачи ======

print("=== ЧАСТЬ 5: Задачи ===\n")

# Задача 2: @log в файл
def log_to_file(filename="lab19_logs.txt"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            with open(filename, "a", encoding="utf-8") as f:
                f.write(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"Функция: {func.__name__} | "
                    f"Аргументы: {args} {kwargs} | "
                    f"Результат: {result} | "
                    f"Время: {elapsed:.6f} сек\n"
                )
            return result
        return wrapper
    return decorator

@log_to_file("lab19_logs.txt")
def mul(a, b):
    return a * b

print("Тест @log (запись в lab19_logs.txt):")
mul(4, 5)
mul(10, 20)
print("  Проверь файл lab19_logs.txt")
with open("lab19_logs.txt", encoding="utf-8") as f:
    print(f.read())

# Задача 3: @memoize для рекурсии
def memoize(func):
    cache = {}
    @wraps(func)
    def wrapper(n):
        if n not in cache:
            cache[n] = func(n)
        return cache[n]
    return wrapper

@memoize
def fib_memo(n):
    if n <= 1:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)

print(f"\n@memoize fib(40) = {fib_memo(40)}")
