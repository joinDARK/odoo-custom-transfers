/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";

// Функция для применения фона калькуляторам
function applyCalculatorBackground() {
    console.log("Применяю фон для калькуляторов...");
    
    // Ищем элементы калькуляторов
    const calculatorForms = document.querySelectorAll('.calculator-form-background, [class*="calculator-form-background"]');
    const calculatorLists = document.querySelectorAll('.calculator-list-background, [class*="calculator-list-background"]');
    
    // Применяем стили к формам
    calculatorForms.forEach(form => {
        form.style.background = 'linear-gradient(135deg, #fce7f3, #f9a8d4, #ec4899)';
        form.style.backgroundImage = 'url("/amanat/static/src/img/calculator_bg_optimized.jpg")';
        form.style.backgroundSize = 'cover';
        form.style.backgroundRepeat = 'no-repeat';
        form.style.backgroundPosition = 'center';
        form.style.minHeight = '100vh';
        console.log("Фон применен к форме:", form);
    });
    
    // Применяем стили к спискам
    calculatorLists.forEach(list => {
        list.style.background = 'linear-gradient(135deg, #fce7f3, #f9a8d4, #ec4899)';
        list.style.backgroundImage = 'url("/amanat/static/src/img/calculator_bg_optimized.jpg")';
        list.style.backgroundSize = 'cover';
        list.style.backgroundRepeat = 'no-repeat';
        list.style.backgroundPosition = 'center';
        list.style.minHeight = '100vh';
        console.log("Фон применен к списку:", list);
    });
    
    // Ищем по data-model
    const calculatorViews = document.querySelectorAll('[data-model*="calculator"]');
    calculatorViews.forEach(view => {
        view.style.background = 'linear-gradient(135deg, #fce7f3, #f9a8d4, #ec4899)';
        view.style.backgroundImage = 'url("/amanat/static/src/img/calculator_bg_optimized.jpg")';
        view.style.backgroundSize = 'cover';
        view.style.backgroundRepeat = 'no-repeat';
        view.style.backgroundPosition = 'center';
        view.style.minHeight = '100vh';
        console.log("Фон применен к view:", view);
    });
}

// Применяем фон при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(applyCalculatorBackground, 100);
    setTimeout(applyCalculatorBackground, 500);
    setTimeout(applyCalculatorBackground, 1000);
});

// Применяем фон при изменении DOM
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            setTimeout(applyCalculatorBackground, 100);
        }
    });
});

observer.observe(document.body, { childList: true, subtree: true });

console.log("Calculator background script loaded!"); 