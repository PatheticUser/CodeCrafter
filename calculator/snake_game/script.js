const gameCanvas = document.getElementById('gameCanvas');
const ctx = gameCanvas.getContext('2d');
const themeToggle = document.getElementById('themeToggle');
const body = document.body;

const gridSize = 20;
let snake = [{ x: 10, y: 10 }];
let food = {};
let dx = 0;
let dy = 0;
let score = 0;
let changingDirection = false;
let gameInterval;
let gameSpeed = 150; // Milliseconds between updates

function generateFood() {
    food = {
        x: Math.floor(Math.random() * (gameCanvas.width / gridSize)),
        y: Math.floor(Math.random() * (gameCanvas.height / gridSize))
    };
}

function drawRect(x, y, color) {
    ctx.fillStyle = color;
    ctx.strokeStyle = 'black';
    ctx.fillRect(x * gridSize, y * gridSize, gridSize, gridSize);
    ctx.strokeRect(x * gridSize, y * gridSize, gridSize, gridSize);
}

function drawSnake() {
    snake.forEach(segment => drawRect(segment.x, segment.y, 'lime'));
}

function drawFood() {
    drawRect(food.x, food.y, 'red');
}

function clearCanvas() {
    ctx.clearRect(0, 0, gameCanvas.width, gameCanvas.height);
}

function moveSnake() {
    const head = { x: snake[0].x + dx, y: snake[0].y + dy };
    snake.unshift(head);

    const didEatFood = head.x === food.x && head.y === food.y;
    if (didEatFood) {
        score += 10;
        generateFood();
    } else {
        snake.pop();
    }
}

function checkCollision() {
    for (let i = 4; i < snake.length; i++) {
        if (snake[i].x === snake[0].x && snake[i].y === snake[0].y) return true;
    }

    const hitLeftWall = snake[0].x < 0;
    const hitRightWall = snake[0].x >= gameCanvas.width / gridSize;
    const hitTopWall = snake[0].y < 0;
    const hitBottomWall = snake[0].y >= gameCanvas.height / gridSize;

    return hitLeftWall || hitRightWall || hitTopWall || hitBottomWall;
}

function gameOver() {
    clearInterval(gameInterval);
    alert(`Game Over! Score: ${score}. Press R to restart.`);
}

function gameLoop() {
    changingDirection = false;
    if (checkCollision()) {
        gameOver();
        return;
    }
    clearCanvas();
    drawFood();
    moveSnake();
    drawSnake();
}

function changeDirection(event) {
    const LEFT_KEY = 37;
    const RIGHT_KEY = 39;
    const UP_KEY = 38;
    const DOWN_KEY = 40;

    if (changingDirection) return;
    changingDirection = true;

    const keyPressed = event.keyCode;
    const goingUp = dy === -1;
    const goingDown = dy === 1;
    const goingRight = dx === 1;
    const goingLeft = dx === -1;

    if (keyPressed === LEFT_KEY && !goingRight) {
        dx = -1;
        dy = 0;
    }

    if (keyPressed === UP_KEY && !goingDown) {
        dx = 0;
        dy = -1;
    }

    if (keyPressed === RIGHT_KEY && !goingLeft) {
        dx = 1;
        dy = 0;
    }

    if (keyPressed === DOWN_KEY && !goingUp) {
        dx = 0;
        dy = 1;
    }

    if (keyPressed === 82) { // 'R' key for restart
        restartGame();
    }
}

function restartGame() {
    clearInterval(gameInterval);
    snake = [{ x: 10, y: 10 }];
    dx = 0;
    dy = 0;
    score = 0;
    changingDirection = false;
    generateFood();
    gameInterval = setInterval(gameLoop, gameSpeed);
}

function toggleTheme() {
    if (themeToggle.checked) {
        body.classList.add('dark-theme');
        body.classList.remove('light-theme');
    } else {
        body.classList.add('light-theme');
        body.classList.remove('dark-theme');
    }
}

// Initial setup
document.addEventListener('keydown', changeDirection);
themeToggle.addEventListener('change', toggleTheme);
generateFood();
restartGame(); // Start the game immediately
toggleTheme(); // Apply initial theme based on checkbox state
