// Скрипт для замены красных цветов на синие в дашборде
// Запустить этой командой: node color_replacements.js

const fs = require('fs');
const path = require('path');

const filePath = './amanat_dashboard.js';

// Читаем файл
let content = fs.readFileSync(filePath, 'utf8');

// Замены цветов
const colorReplacements = [
    // Красные цвета -> синие
    { from: '#ef4444', to: '#1e40af' },  // Красный -> темно-синий
    { from: '#dc2626', to: '#1e3a8a' },  // Темно-красный -> очень темно-синий
    { from: 'rgba(239, 68, 68, 0.15)', to: 'rgba(30, 64, 175, 0.15)' },  // Красный с прозрачностью
    { from: '#f87171', to: '#93c5fd' },  // Светло-красный -> светло-синий
];

// Выполняем замены
colorReplacements.forEach(replacement => {
    const regex = new RegExp(replacement.from.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
    content = content.replace(regex, replacement.to);
});

// Записываем обратно
fs.writeFileSync(filePath, content);

console.log('Замены цветов выполнены успешно!'); 