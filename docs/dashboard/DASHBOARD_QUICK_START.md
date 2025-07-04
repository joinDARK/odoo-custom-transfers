# 🚀 Быстрый старт с Amanat Dashboard

## 📋 Минимальные требования

- ✅ Odoo 18
- ✅ Python 3.11+
- ✅ PostgreSQL 13+
- ✅ Модуль Amanat установлен

## ⚡ Установка за 5 минут

### 1. Обновите модуль
```bash
cd /home/incube/Documents/odoo
./odoo-bin -c odoo.conf -u amanat -d mydb
```

### 2. Очистите кеш браузера
```
Ctrl + Shift + F5
```

### 3. Откройте дашборд
Перейдите в: **Amanat → Дашборд → Аналитический дашборд**

## 🎯 Частые задачи

### Как добавить новый график?

**1. Добавьте данные в backend:**
```python
# В файле models/dashboard.py, метод get_dashboard_data
new_data = self.env['amanat.model'].read_group(
    domain=domain,
    fields=['field_name'],
    groupby=['field_name']
)
result['new_data'] = new_data
```

**2. Обновите frontend состояние:**
```javascript
// В файле static/src/js/amanat_dashboard.js, метод updateStateFromData
this.state.newData = data.new_data || [];
```

**3. Добавьте рендеринг:**
```javascript
// В методе initializeAllCharts
if (this.state.newData.length > 0) {
    this.renderBarChart('new-data-chart', {
        labels: this.state.newData.map(d => d.field_name),
        data: this.state.newData.map(d => d.field_name_count),
        title: 'Новый график'
    });
}
```

**4. Добавьте canvas в шаблон:**
```xml
<!-- В файле static/src/xml/amanat_dashboard.xml -->
<div class="col-md-6">
    <div class="chart-container">
        <canvas id="new-data-chart"/>
    </div>
</div>
```

### Как добавить новую метрику?

**1. Backend:**
```python
# В get_dashboard_data
result['new_metric'] = self.env['amanat.model'].search_count(domain)
```

**2. Frontend:**
```javascript
// В updateStateFromData
this.state.newMetric = data.new_metric || 0;
```

**3. Шаблон:**
```xml
<div class="metric-card">
    <h3>Новая метрика</h3>
    <div class="metric-value">
        <t t-esc="formatNumber(state.newMetric)"/>
    </div>
</div>
```

### Как изменить цвета графиков?

```javascript
// В методах рендеринга графиков
backgroundColor: [
    'rgba(255, 99, 132, 0.8)',   // Красный
    'rgba(54, 162, 235, 0.8)',   // Синий
    'rgba(255, 206, 86, 0.8)',   // Желтый
    'rgba(75, 192, 192, 0.8)',   // Бирюзовый
    'rgba(153, 102, 255, 0.8)'   // Фиолетовый
]
```

### Как добавить фильтр по менеджеру?

**1. Добавьте в состояние:**
```javascript
this.state.filters = {
    manager: null
};
```

**2. Передайте в backend:**
```javascript
const params = {
    date_from: this.state.dateRange1.start,
    date_to: this.state.dateRange1.end,
    manager_id: this.state.filters.manager
};
```

**3. Используйте в backend:**
```python
if manager_id:
    domain.append(('manager_id', '=', manager_id))
```

## 🔥 Горячие клавиши

- `F5` - Обновить дашборд
- `Ctrl+Shift+F5` - Полная очистка кеша
- `F12` - Открыть консоль разработчика

## 🐛 Отладка

### Включить логирование
```javascript
// В начале любого метода
console.log('Method called:', arguments);
console.log('Current state:', this.state);
```

### Проверить загрузку Chart.js
```javascript
// В консоли браузера
typeof Chart !== 'undefined'  // должно вернуть true
```

### Проверить данные от сервера
```javascript
// В loadDashboardData после получения data
console.log('Server response:', data);
```

## 📊 Примеры готовых графиков

### Круговая диаграмма с процентами
```javascript
this.renderPieChartWithPercentage('my-pie-chart', {
    labels: ['Категория 1', 'Категория 2', 'Категория 3'],
    data: [30, 50, 20],
    title: 'Распределение по категориям'
});
```

### Линейный график
```javascript
this.renderLineChart('my-line-chart', {
    labels: ['Янв', 'Фев', 'Мар', 'Апр', 'Май'],
    data: [10, 25, 30, 45, 60],
    title: 'Динамика роста'
});
```

### Горизонтальный столбчатый график
```javascript
this.renderHorizontalBarChart('my-bar-chart', {
    labels: ['Товар А', 'Товар Б', 'Товар В'],
    data: [100, 150, 80],
    title: 'Топ товаров'
});
```

## 💡 Полезные советы

### 1. Производительность
- Используйте `read_group` вместо `search` + цикл
- Ограничивайте количество записей в топах (limit=10)
- Кешируйте тяжелые вычисления

### 2. UX/UI
- Показывайте индикатор загрузки
- Обрабатывайте ошибки gracefully
- Используйте анимации для плавности

### 3. Безопасность
- Всегда проверяйте права доступа
- Валидируйте входные данные
- Не передавайте чувствительные данные

## 🆘 Быстрая помощь

### Ошибка: "Service rpc is not available"
```javascript
// Используйте
this.orm = useService("orm");
// Вместо
this.rpc = useService("rpc");  // Не работает в Odoo 18
```

### Ошибка: "Field does not exist"
1. Проверьте имя поля в модели
2. Обновите модуль: `./odoo-bin -u amanat`
3. Перезапустите сервер

### Графики не отображаются
1. Откройте консоль браузера (F12)
2. Проверьте ошибки JavaScript
3. Убедитесь что Chart.js загружен
4. Проверьте ID canvas элементов

## 📚 Дополнительные ресурсы

- [Полная документация](./DASHBOARD_COMPLETE_GUIDE.md)
- [Структура кода](./DASHBOARD_CODE_STRUCTURE.md)
- [Официальная документация Odoo 18](https://www.odoo.com/documentation/18.0/)
- [Chart.js документация](https://www.chartjs.org/docs/latest/)
- [OWL Framework](https://github.com/odoo/owl)

## 🎉 Готово!

Теперь у вас есть полностью функциональный дашборд с:
- ✅ 18+ типов графиков
- ✅ Реал-тайм данные
- ✅ Фильтрация по датам
- ✅ Красивый тёмный дизайн
- ✅ Адаптивная верстка

**Удачной разработки! 🚀**

---

*Версия: 1.0.0 | Последнее обновление: 02.07.2025* 