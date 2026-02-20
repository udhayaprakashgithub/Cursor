const form = document.getElementById('task-form');
const scheduleList = document.getElementById('schedule-list');
const template = document.getElementById('task-template');

const tasks = [];

function renderTasks() {
  scheduleList.innerHTML = '';

  if (!tasks.length) {
    const empty = document.createElement('li');
    empty.textContent = 'No tasks yet. Add one above to start planning your day.';
    empty.style.color = '#6b7280';
    scheduleList.appendChild(empty);
    return;
  }

  tasks
    .slice()
    .sort((a, b) => a.start.localeCompare(b.start))
    .forEach((task) => {
      const node = template.content.cloneNode(true);
      node.querySelector('.time-range').textContent = `${task.start} - ${task.end}`;
      node.querySelector('.task-title').textContent = task.name;

      node.querySelector('.delete-btn').addEventListener('click', () => {
        const index = tasks.findIndex((t) => t.id === task.id);
        if (index >= 0) {
          tasks.splice(index, 1);
          renderTasks();
        }
      });

      scheduleList.appendChild(node);
    });
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  const taskName = document.getElementById('task-name').value.trim();
  const taskStart = document.getElementById('task-start').value;
  const taskEnd = document.getElementById('task-end').value;

  if (!taskName || taskStart >= taskEnd) {
    alert('Please enter a task name and choose a valid time range.');
    return;
  }

  tasks.push({
    id: crypto.randomUUID(),
    name: taskName,
    start: taskStart,
    end: taskEnd,
  });

  form.reset();
  renderTasks();
});

renderTasks();
