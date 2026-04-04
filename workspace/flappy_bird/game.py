import pygame
import random

# Initialize pygame
pygame.init()

# Game constants
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_SPEED = 3
PIPE_GAP = 150

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
YELLOW = (255, 255, 0)

# Setup screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 36)

class Bird:
    def __init__(self):
        self.x = 100
        self.y = SCREEN_HEIGHT // 2
        self.velocity = 0
        self.radius = 15
    
    def flap(self):
        self.velocity = FLAP_STRENGTH
    
    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity
    
    def draw(self):
        pygame.draw.circle(screen, YELLOW, (self.x, int(self.y)), self.radius)
        pygame.draw.circle(screen, BLACK, (self.x, int(self.y)), self.radius, 2)

class Pipe:
    def __init__(self):
        self.x = SCREEN_WIDTH
        self.width = 60
        self.gap_y = random.randint(150, SCREEN_HEIGHT - 150)
        self.passed = False
    
    def update(self):
        self.x -= PIPE_SPEED
    
    def draw(self):
        # Top pipe
        pygame.draw.rect(screen, GREEN, (self.x, 0, self.width, self.gap_y - self.gap // 2))
        # Bottom pipe
        pygame.draw.rect(screen, GREEN, (self.x, self.gap_y + self.gap // 2, self.width, SCREEN_HEIGHT - self.gap_y - self.gap // 2))
    
    def collides_with(self, bird):
        # Check if bird is within pipe's x range
        if bird.x + bird.radius > self.x and bird.x - bird.radius < self.x + self.width:
            # Check if bird hits top or bottom pipe
            if bird.y - bird.radius < self.gap_y - self.gap // 2 or bird.y + bird.radius > self.gap_y + self.gap // 2:
                return True
        return False

def main():
    bird = Bird()
    pipes = []
    score = 0
    pipe_timer = 0
    running = True
    game_over = False
    
    while running:
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_over:
                        # Restart game
                        bird = Bird()
                        pipes = []
                        score = 0
                        pipe_timer = 0
                        game_over = False
                    else:
                        bird.flap()
        
        if not game_over:
            # Update bird
            bird.update()
            
            # Check if bird hits ground or ceiling
            if bird.y + bird.radius >= SCREEN_HEIGHT or bird.y - bird.radius <= 0:
                game_over = True
            
            # Generate pipes
            pipe_timer += 1
            if pipe_timer >= 90:
                pipes.append(Pipe())
                pipe_timer = 0
            
            # Update pipes
            for pipe in pipes[:]:
                pipe.update()
                
                # Check collision
                if pipe.collides_with(bird):
                    game_over = True
                
                # Check if bird passed pipe
                if not pipe.passed and pipe.x + pipe.width < bird.x:
                    score += 1
                    pipe.passed = True
                
                # Remove off-screen pipes
                if pipe.x + pipe.width < 0:
                    pipes.remove(pipe)
        
        # Draw everything
        screen.fill(WHITE)
        
        # Draw pipes
        for pipe in pipes:
            pipe.draw()
        
        # Draw bird
        bird.draw()
        
        # Draw score
        score_text = font.render(f"Score: {score}", True, BLACK)
        screen.blit(score_text, (10, 10))
        
        # Draw game over message
        if game_over:
            game_over_text = font.render("Game Over! Press SPACE", True, BLACK)
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(game_over_text, text_rect)
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
