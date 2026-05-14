import pygame
import sys
import random

class SnakeGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((800, 600))
        self.clock = pygame.time.Clock()
        self.snake = [(200, 200), (220, 200), (240, 200)]
        self.direction = 'right'
        self.apple = self.set_apple()
        self.score = 0
    
    def set_apple(self):
        return (random.randint(0, 780) // 20 * 20, random.randint(0, 580) // 20 * 20)
    
    def update(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and self.direction != 'down':
                    self.direction = 'up'
                elif event.key == pygame.K_DOWN and self.direction != 'up':
                    self.direction = 'down'
                elif event.key == pygame.K_LEFT and self.direction != 'right':
                    self.direction = 'left'
                elif event.key == pygame.K_RIGHT and self.direction != 'left':
                    self.direction = 'right'
        head = self.snake[-1]
        if self.direction == 'up':
            new_head = (head[0], head[1] - 20)
        elif self.direction == 'down':
            new_head = (head[0], head[1] + 20)
        elif self.direction == 'left':
            new_head = (head[0] - 20, head[1])
        elif self.direction == 'right':
            new_head = (head[0] + 20, head[1])
        self.snake.append(new_head)
        if self.snake[-1] == self.apple:
            self.apple = self.set_apple()
            self.score += 1
        else:
            self.snake.pop(0)
        if (self.snake[-1][0] < 0 or self.snake[-1][0] >= 800 or
            self.snake[-1][1] < 0 or self.snake[-1][1] >= 600 or
            self.snake[-1] in self.snake[:-1]):
            pygame.quit()
            sys.exit()
    
    def draw(self):
        self.screen.fill((30, 30, 30))
        for pos in self.snake:
            pygame.draw.rect(self.screen, (0, 255, 100), (pos[0], pos[1], 20, 20))
        pygame.draw.rect(self.screen, (255, 100, 100), (self.apple[0], self.apple[1], 20, 20))
        font = pygame.font.Font(None, 36)
        text = font.render(f'Score: {self.score}', True, (255, 255, 255))
        self.screen.blit(text, (10, 10))
        pygame.display.flip()