import sys
sys.path.append(r"D:\\Code\\CodeCrafter\\.venv\\Lib\\site-packages")
import pygame
import sys
from game import SnakeGame

def main():
    pygame.init()
    game = SnakeGame()
    while True:
        game.update()
        game.draw()
        pygame.time.Clock().tick(10)

if __name__ == '__main__':
    main()