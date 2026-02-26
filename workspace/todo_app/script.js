document.addEventListener('DOMContentLoaded', () => {
    const todoInput = document.getElementById('todo-input');
    const dueDateInput = document.getElementById('due-date-input');
    const categoryInput = document.getElementById('category-input');
    const priorityInput = document.getElementById('priority-input');
    const addTodoBtn = document.getElementById('add-todo-btn');
    const todoList = document.getElementById('todo-list');
    const categoryFilter = document.getElementById('category-filter');
    const priorityFilter = document.getElementById('priority-filter');

    let todos = JSON.parse(localStorage.getItem('todos')) || [];

    const saveTodos = () => {
        localStorage.setItem('todos', JSON.stringify(todos));
    };

    const renderTodos = () => {
        todoList.innerHTML = '';
        const filterCategory = categoryFilter.value;
        const filterPriority = priorityFilter.value;

        todos.filter(todo => 
                (filterCategory === 'all' || todo.category === filterCategory) &&
                (filterPriority === 'all' || todo.priority === filterPriority)
            )
             .forEach(todo => {
            const li = document.createElement('li');
            li.className = todo.completed ? 'completed' : '';
            li.innerHTML = `
                <div class="todo-details">
                    <span>[${todo.category}] ${todo.text}</span>
                    <div class="todo-meta">
                        ${todo.dueDate ? `Due: ${todo.dueDate}` : ''}
                        ${todo.priority ? `| Priority: ${todo.priority}` : ''}
                    </div>
                </div>
                <button data-id="${todo.id}">Delete</button>
            `;

            li.querySelector('span').addEventListener('click', () => {
                todo.completed = !todo.completed;
                saveTodos();
                renderTodos();
            });

            li.querySelector('button').addEventListener('click', (e) => {
                todos = todos.filter(t => t.id !== todo.id);
                saveTodos();
                renderTodos();
            });
            todoList.appendChild(li);
        });
        updateFilterOptions();
    };

    const addTodo = () => {
        const text = todoInput.value.trim();
        const dueDate = dueDateInput.value;
        const category = categoryInput.value;
        const priority = priorityInput.value;

        if (text === '') {
            alert('Todo cannot be empty!');
            return;
        }

        const newTodo = {
            id: Date.now(),
            text,
            dueDate,
            category,
            priority,
            completed: false
        };

        todos.push(newTodo);
        saveTodos();
        todoInput.value = '';
        dueDateInput.value = '';
        renderTodos();
    };

    const updateFilterOptions = () => {
        // Update Category Filter
        categoryFilter.innerHTML = '<option value="all">All</option>';
        const uniqueCategories = [...new Set(todos.map(todo => todo.category))];
        uniqueCategories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            categoryFilter.appendChild(option);
        });
        categoryFilter.value = categoryFilter.dataset.current || 'all';

        // Update Priority Filter (static options for now, can be dynamic)
        priorityFilter.innerHTML = '<option value="all">All</option>';
        const uniquePriorities = [...new Set(todos.map(todo => todo.priority))].filter(p => p);
        const priorityOrder = {'High': 3, 'Medium': 2, 'Low': 1};
        uniquePriorities.sort((a,b) => priorityOrder[b] - priorityOrder[a]);

        uniquePriorities.forEach(priority => {
            const option = document.createElement('option');
            option.value = priority;
            option.textContent = priority;
            priorityFilter.appendChild(option);
        });
        priorityFilter.value = priorityFilter.dataset.current || 'all';
    };

    addTodoBtn.addEventListener('click', addTodo);
    categoryFilter.addEventListener('change', () => {
        categoryFilter.dataset.current = categoryFilter.value;
        renderTodos();
    });
    priorityFilter.addEventListener('change', () => {
        priorityFilter.dataset.current = priorityFilter.value;
        renderTodos();
    });

    renderTodos();
});