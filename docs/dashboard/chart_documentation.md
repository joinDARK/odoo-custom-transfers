# 📊 Документация по использованию графиков в AmanatDashboard (Odoo OWL + Chart.js)

## 🔧 Основы

В дашборде используются графики на базе **Chart.js**. Каждый график инициализируется с помощью JavaScript-функций, которые создают экземпляры `new Chart()` и привязывают их к `<canvas>` элементам.

## 📁 Структура вызова

Каждый график инициализируется так:

```js
this.renderBarChart('canvas-id', {
    labels: [...],
    data: [...],
    title: "Название графика"
});
```

---

## 🧰 Список доступных функций отрисовки

### 1. `renderPieChartWithPercentage(canvasId, { labels, data, title })`

**Тип:** круговая диаграмма (pie) с отображением процентов.

**Параметры:**
- `canvasId` — ID элемента `<canvas>`
- `labels` — массив подписей секторов
- `data` — массив значений
- `title` — заголовок графика

**Пример:**
```js
this.renderPieChartWithPercentage('my-pie', {
    labels: ['USD', 'EUR', 'BTC'],
    data: [1000, 500, 300],
    title: 'Распределение по валютам'
});
```

---

### 2. `renderBarChart(canvasId, { labels, data, title })`

**Тип:** вертикальный столбчатый график (bar)

**Пример:**
```js
this.renderBarChart('bar-chart', {
    labels: ['A', 'B', 'C'],
    data: [30, 20, 50],
    title: 'Пример Bar графика'
});
```

---

### 3. `renderHorizontalBarChart(canvasId, { labels, data, title })`

**Тип:** горизонтальный столбчатый график

**Пример:**
```js
this.renderHorizontalBarChart('horizontal-bar', {
    labels: ['USA', 'Germany', 'China'],
    data: [200, 150, 100],
    title: 'Продажи по странам'
});
```

---

### 4. `renderLineChart(canvasId, { labels, data, title })`

**Тип:** линейный график

**Пример:**
```js
this.renderLineChart('line-sales', {
    labels: ['Янв', 'Фев', 'Мар'],
    data: [1000, 1100, 1050],
    title: 'Продажи по месяцам'
});
```

---

### 5. `renderComparisonLineChart(canvasId, { labels, data1, data2, title1, title2 })`

**Тип:** линейный график с двумя линиями (сравнение)

**Пример:**
```js
this.renderComparisonLineChart('compare-lines', {
    labels: ['Week 1', 'Week 2', 'Week 3'],
    data1: [100, 200, 300],
    data2: [90, 210, 280],
    title1: 'Период 1',
    title2: 'Период 2'
});
```

---

## ⚠️ Важно

- `canvasId` должен соответствовать ID элемента `<canvas>` в шаблоне XML/OWL.
- Все функции используют `Chart.js`, который динамически загружается, если ещё не подгружен.
- Старые графики уничтожаются (`chart.destroy()`) перед созданием новых.
- Вызывай графики **только после загрузки данных и монтирования DOM**.

---

## ✅ Рекомендации

- Используй `onMounted()` или ручной вызов при клике/выборе.
- Убедись, что `Chart.js` загружен через `loadChartJS()` перед инициализацией.
- Для сложных графиков создай свою функцию на базе `new Chart()`.

---

## 📌 Пример кастомной функции

```js
renderCustomRadarChart(canvasId, { labels, data, title }) {
    const ctx = document.getElementById(canvasId);
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels,
            datasets: [{
                label: title,
                data,
                fill: true,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            responsive: true
        }
    });
}
```

---

## 📞 Поддержка

Для добавления новых типов графиков или динамических данных — создай новую функцию отрисовки и используй `this.state` или ORM-запросы для получения данных.