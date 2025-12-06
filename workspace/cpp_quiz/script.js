const questionElement = document.getElementById('question');
const answerButtonsElement = document.getElementById('answer-buttons');
const nextButton = document.getElementById('next-btn');
const timerBar = document.getElementById('timer-bar');
const timeLeftSpan = document.getElementById('time-left');

const QUESTION_TIME = 5; // 5 seconds per question
let currentQuestionIndex = 0;
let score = 0;
let timer;
let timeRemaining;

const questions = [
    {
        question: 'Which keyword is used to define a function in Python?',
        answers: [
            { text: 'func', correct: false },
            { text: 'def', correct: true },
            { text: 'function', correct: false },
            { text: 'define', correct: false }
        ]
    },
    {
        question: 'What is the output of `print(type([]))` in Python?',
        answers: [
            { text: '<class \'tuple\'>', correct: false },
            { text: '<class \'list\'>', correct: true },
            { text: '<class \'dict\'>', correct: false },
            { text: '<class \'set\'>', correct: false }
        ]
    },
    {
        question: 'Which of the following is NOT a fundamental data type in Python?',
        answers: [
            { text: 'int', correct: false },
            { text: 'float', correct: false },
            { text: 'char', correct: true },
            { text: 'str', correct: false }
        ]
    },
    {
        question: 'How do you comment a single line in Python?',
        answers: [
            { text: '// This is a comment', correct: false },
            { text: '/* This is a comment */', correct: false },
            { text: '# This is a comment', correct: true },
            { text: '<!-- This is a comment -->', correct: false }
        ]
    },
    {
        question: 'Which of these is used for iteration over a sequence in Python?',
        answers: [
            { text: 'for loop', correct: true },
            { text: 'while loop', correct: false },
            { text: 'do-while loop', correct: false },
            { text: 'iterate loop', correct: false }
        ]
    }
];

function startQuiz() {
    currentQuestionIndex = 0;
    score = 0;
    nextButton.innerHTML = 'Next';
    nextButton.style.display = 'none';
    showQuestion();
}

function showQuestion() {
    resetState();
    let currentQuestion = questions[currentQuestionIndex];
    questionElement.innerHTML = currentQuestion.question;

    currentQuestion.answers.forEach(answer => {
        const button = document.createElement('button');
        button.innerHTML = answer.text;
        button.classList.add('btn');
        if (answer.correct) {
            button.dataset.correct = answer.correct;
        }
        button.addEventListener('click', selectAnswer);
        answerButtonsElement.appendChild(button);
    });
    startTimer();
}

function resetState() {
    if (timer) {
        clearInterval(timer);
    }
    timerBar.style.width = '100%';
    timeLeftSpan.innerHTML = QUESTION_TIME;
    nextButton.style.display = 'none';
    while (answerButtonsElement.firstChild) {
        answerButtonsElement.removeChild(answerButtonsElement.firstChild);
    }
}

function startTimer() {
    timeRemaining = QUESTION_TIME;
    timerBar.style.width = '100%';
    timeLeftSpan.innerHTML = timeRemaining;

    timer = setInterval(() => {
        timeRemaining--;
        timeLeftSpan.innerHTML = timeRemaining;
        timerBar.style.width = `${(timeRemaining / QUESTION_TIME) * 100}%`;

        if (timeRemaining <= 0) {
            clearInterval(timer);
            // Automatically select an answer (e.g., mark incorrect if no choice made)
            // Or simply move to the next question
            handleNextButton();
        }
    }, 1000);
}

function selectAnswer(e) {
    clearInterval(timer);
    const selectedButton = e.target;
    const isCorrect = selectedButton.dataset.correct === 'true';
    if (isCorrect) {
        selectedButton.classList.add('correct');
        score++;
    } else {
        selectedButton.classList.add('incorrect');
    }
    Array.from(answerButtonsElement.children).forEach(button => {
        if (button.dataset.correct === 'true') {
            button.classList.add('correct');
        }
        button.disabled = true;
    });
    nextButton.style.display = 'block';
}

function handleNextButton() {
    currentQuestionIndex++;
    if (currentQuestionIndex < questions.length) {
        showQuestion();
    } else {
        showScore();
    }
}

function showScore() {
    resetState();
    questionElement.innerHTML = `You scored ${score} out of ${questions.length}!`;
    nextButton.innerHTML = 'Play Again';
    nextButton.style.display = 'block';
}

nextButton.addEventListener('click', () => {
    if (currentQuestionIndex < questions.length) {
        handleNextButton();
    } else {
        startQuiz();
    }
});

startQuiz();