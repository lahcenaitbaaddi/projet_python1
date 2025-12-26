// static/js/main.js
document.addEventListener('DOMContentLoaded', function(){
    const body = document.getElementById('body');
    const toggle = document.getElementById('themeToggle');
    const saved = localStorage.getItem('theme') || 'light';
    if(saved === 'dark') body.classList.add('dark');
  
    toggle && toggle.addEventListener('click', () => {
      body.classList.toggle('dark');
      localStorage.setItem('theme', body.classList.contains('dark') ? 'dark' : 'light');
    });
  });
  