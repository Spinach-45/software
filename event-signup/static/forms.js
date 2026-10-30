'use strict';

document.querySelectorAll('form').forEach((form) => {
    const start = form.querySelector('[name="event_date"]');
    const deadline = form.querySelector('[name="deadline"]');
    const serverNow = Date.parse(form.dataset.serverNow || '');
    const loadedAt = performance.now();
    function update() {
        // 用伺服器台灣時間加上經過時間，避免瀏覽器時區或系統時鐘誤差。
        if (start && deadline && Number.isFinite(serverNow)) {
            const nextMinute = Math.ceil((serverNow + performance.now() - loadedAt) / 60000) * 60000;
            const minimum = new Date(nextMinute + 8 * 3600000).toISOString().slice(0, 16);
            start.min = minimum;
            deadline.min = minimum;
            deadline.max = start.value;
            deadline.setCustomValidity(deadline.value && start.value && deadline.value > start.value
                ? '報名截止時間不能晚於活動時間' : '');
        }
        form.querySelectorAll('[name="name"], [name="title"]').forEach((input) => {
            input.setCustomValidity(input.value && !input.value.trim() ? '請輸入非空白內容' : '');
        });
    }
    form.addEventListener('input', update);
    form.addEventListener('focusout', (event) => {
        if (event.target.matches('input[type="text"], input[type="tel"], textarea')) {
            event.target.value = event.target.value.trim();
            update();
        }
    });
    form.addEventListener('submit', (event) => {
        form.querySelectorAll('input[type="text"], input[type="tel"], textarea').forEach((input) => {
            input.value = input.value.trim();
        });
        update();
        if (!form.reportValidity()) {
            event.preventDefault();
            return;
        }
        if (form.dataset.submitting === 'true') {
            event.preventDefault();
            return;
        }
        form.dataset.submitting = 'true';
    });
    window.addEventListener('pageshow', () => { delete form.dataset.submitting; });
    if (start) setInterval(update, 1000);
    update();
});
