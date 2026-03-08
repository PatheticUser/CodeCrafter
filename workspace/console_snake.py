import random
import curses

current_version = '1.0.0'

def create_game_window():
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)
    curses.curs_set(0)
    height, width = 20, 60
    win = curses.newwin(height, width, 0, 0)
    win.border(1)
    win.timeout(100)
    return win


def game_over_window(win):
    height, width = 5, 40
    game_over = curses.newwin(height, width, 7, 10)
    game_over.border(1)
    return game_over


def main(stdscr):
    win = create_game_window()
    game_over = game_over_window(win)
    
    score = 1
    try:
        # Initial snake and food positions
        snake = [(10, 20), (10, 19), (10, 18)]
        direction = curses.KEY_RIGHT
        
        # Place initial food
        food = (random.randint(1, 18), random.randint(1, 58))
        while food in snake:
            food = (random.randint(1, 18), random.randint(1, 58))
    except Exception as e:
        pass
    finally:
        curses.endwin()

curses.wrapper(main)