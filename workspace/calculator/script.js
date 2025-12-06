document.addEventListener('DOMContentLoaded', () => {
    const display = document.getElementById('display');
    const buttons = document.querySelector('.buttons');

    let currentInput = '0';
    let operator = null;
    let previousInput = null;
    let resetDisplay = false;

    function updateDisplay() {
        display.value = currentInput;
    }

    buttons.addEventListener('click', (e) => {
        const target = e.target;

        if (!target.matches('button')) {
            return;
        }

        if (target.classList.contains('number')) {
            if (resetDisplay) {
                currentInput = target.textContent;
                resetDisplay = false;
            } else {
                currentInput = currentInput === '0' ? target.textContent : currentInput + target.textContent;
            }
            updateDisplay();
        } else if (target.classList.contains('operator')) {
            if (operator && !resetDisplay) {
                calculate();
            }
            previousInput = currentInput;
            operator = target.textContent;
            resetDisplay = true;
        } else if (target.classList.contains('equals')) {
            calculate();
            operator = null;
        } else if (target.classList.contains('clear')) {
            currentInput = '0';
            operator = null;
            previousInput = null;
            resetDisplay = false;
            updateDisplay();
        } else if (target.classList.contains('decimal')) {
            if (resetDisplay) {
                currentInput = '0.';
                resetDisplay = false;
            } else if (!currentInput.includes('.')) {
                currentInput += '.';
            }
            updateDisplay();
        }
    });

    function calculate() {
        if (!operator || previousInput === null) {
            return;
        }

        let result;
        const prev = parseFloat(previousInput);
        const current = parseFloat(currentInput);

        if (isNaN(prev) || isNaN(current)) {
            return;
        }

        switch (operator) {
            case '+':
                result = prev + current;
                break;
            case '-':
                result = prev - current;
                break;
            case '*':
                result = prev * current;
                break;
            case '/':
                result = prev / current;
                break;
            default:
                return;
        }
        currentInput = result.toString();
        updateDisplay();
        resetDisplay = true;
    }

    updateDisplay();
});