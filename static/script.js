document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;

    // 1. Set Today's Date (if the element exists)
    const dateElement = document.getElementById('current-date');
    if (dateElement) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateElement.textContent = new Date().toLocaleDateString('en-US', options);
    }

    // 2. Apply saved theme on load
    const currentTheme = localStorage.getItem('theme');
    if (currentTheme === 'dark') {
        body.setAttribute('data-theme', 'dark');
        if (themeToggle) themeToggle.textContent = '☀️';
    }

    // 3. Toggle Logic
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            if (body.getAttribute('data-theme') === 'dark') {
                body.removeAttribute('data-theme');
                themeToggle.textContent = '🌙';
                localStorage.setItem('theme', 'light');
            } else {
                body.setAttribute('data-theme', 'dark');
                themeToggle.textContent = '☀️';
                localStorage.setItem('theme', 'dark');
            }
        });
    }
});