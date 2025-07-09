// Простая реализация кнопки переключения chatter для всех форм с логами
(function() {
    'use strict';
    
    let chatterVisible = true; // По умолчанию chatter видим
    let toggleButton = null;
    
    function createToggleButton() {
        if (toggleButton) return; // Кнопка уже создана
        
        // Находим место в верхнем меню для вставки кнопки
        const navbar = document.querySelector('.o_main_navbar .o_menu_systray');
        if (!navbar) {
            console.log('Chatter Toggle: navbar не найден');
            return;
        }
        
        toggleButton = document.createElement('button');
        toggleButton.className = 'chatter-toggle-btn';
        toggleButton.innerHTML = '<i class="fa fa-eye-slash"></i>';
        toggleButton.type = 'button';
        toggleButton.title = 'Скрыть логи';
        
        // Минималистичные стили для интеграции в navbar без li контейнера
        toggleButton.style.cssText = `
            background: none !important;
            border: none !important;
            color: #6c757d !important;
            cursor: pointer !important;
            font-size: 16px !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 !important;
            margin: 0 8px !important;
            height: 40px !important;
            width: 40px !important;
            border-radius: 4px !important;
            list-style: none !important;
            vertical-align: middle !important;
            line-height: 1 !important;
            align-self: center !important;
        `;
        
        toggleButton.addEventListener('click', toggleChatter);
        toggleButton.addEventListener('mouseenter', function() {
            this.style.color = '#495057';
            this.style.backgroundColor = 'rgba(0,0,0,0.05)';
        });
        toggleButton.addEventListener('mouseleave', function() {
            this.style.color = chatterVisible ? '#dc3545' : '#6c757d';
            this.style.backgroundColor = 'transparent';
        });
        
        // Вставляем кнопку прямо в navbar без li контейнера
        navbar.insertBefore(toggleButton, navbar.firstChild);
        console.log('Chatter Toggle: кнопка создана и добавлена в navbar');
    }
    
    function removeToggleButton() {
        if (toggleButton) {
            toggleButton.remove();
            toggleButton = null;
            console.log('Chatter Toggle: кнопка удалена');
        }
    }
    
    function toggleChatter() {
        const chatters = document.querySelectorAll('.o-mail-Chatter, .o-mail-ChatterContainer, .o-mail-Form-chatter');
        console.log('Chatter Toggle: найдено чэттеров:', chatters.length);
        
        if (chatterVisible) {
            // Скрываем chatter
            chatters.forEach(chatter => {
                chatter.style.display = 'none';
            });
            toggleButton.innerHTML = '<i class="fa fa-eye"></i>';
            toggleButton.title = 'Показать логи';
            toggleButton.style.color = '#6c757d';
            chatterVisible = false;
            console.log('Chatter Toggle: чэттеры скрыты');
        } else {
            // Показываем chatter
            chatters.forEach(chatter => {
                chatter.style.display = '';
            });
            toggleButton.innerHTML = '<i class="fa fa-eye-slash"></i>';
            toggleButton.title = 'Скрыть логи';
            toggleButton.style.color = '#dc3545';
            chatterVisible = true;
            console.log('Chatter Toggle: чэттеры показаны');
        }
    }
    
    function checkIfFormWithChatter() {
        // Проверяем наличие любой формы с chatter
        const hasForm = document.querySelector('.o_form_view');
        if (!hasForm) return false;
        
        // Проверяем наличие различных chatter элементов
        const hasChatter = (
            document.querySelector('.o-mail-Chatter') || 
            document.querySelector('.o-mail-ChatterContainer') || 
            document.querySelector('.o-mail-Form-chatter') ||
            // Проверяем в DOM наличие полей chatter
            document.querySelector('[name="message_ids"]') ||
            document.querySelector('[name="message_follower_ids"]') ||
            document.querySelector('[name="activity_ids"]') ||
            // Проверяем div с классами для chatter
            document.querySelector('.oe_chatter') ||
            document.querySelector('.o_mail_thread') ||
            // Проверяем наличие form view с mail.thread наследованием
            document.querySelector('.o_form_view .o-mail-Chatter')
        );
        
        return hasForm && hasChatter;
    }
    
    function initChatterToggle() {
        if (checkIfFormWithChatter()) {
            console.log('Chatter Toggle: форма с чэттером найдена');
            createToggleButton();
        } else {
            console.log('Chatter Toggle: форма с чэттером не найдена');
            removeToggleButton();
        }
    }
    
    // Инициализация при загрузке DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initChatterToggle);
    } else {
        initChatterToggle();
    }
    
    // Отслеживание изменений в DOM для SPA (Single Page Application)
    let lastUrl = location.href;
    new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(initChatterToggle, 500);
        }
    }).observe(document, { subtree: true, childList: true });
    
    // Оптимизированная проверка с debounce
    let checkTimeout = null;
    function debouncedCheck() {
        if (checkTimeout) clearTimeout(checkTimeout);
        checkTimeout = setTimeout(() => {
            if (checkIfFormWithChatter() && !toggleButton) {
                createToggleButton();
            } else if (!checkIfFormWithChatter() && toggleButton) {
                removeToggleButton();
            }
        }, 500);
    }
    
    // Проверка каждые 3 секунды
    setInterval(debouncedCheck, 3000);
    
})();

// Запасной вариант через jQuery, если он доступен
if (typeof $ !== 'undefined') {
    $(document).ready(function() {
        setTimeout(function() {
            // Дополнительная проверка через jQuery
            function addChatterToggleJQuery() {
                const isFormWithChatter = (
                    $('.o_form_view').length > 0 &&
                    ($('.o-mail-Chatter').length > 0 ||
                     $('.o-mail-ChatterContainer').length > 0 ||
                     $('.o-mail-Form-chatter').length > 0 ||
                     $('[name="message_ids"]').length > 0 ||
                     $('[name="message_follower_ids"]').length > 0 ||
                     $('[name="activity_ids"]').length > 0)
                );
                
                if (isFormWithChatter && !$('.chatter-toggle-btn').length) {
                    console.log('Добавляем кнопку переключения chatter для формы с логами через jQuery');
                    // Логика для создания кнопки здесь будет выполнена основным скriptом
                }
            }
            
            addChatterToggleJQuery();
            
            // Отслеживание навигации
            $(document).on('click', 'a, .o_pager_next, .o_pager_previous', function() {
                setTimeout(addChatterToggleJQuery, 1000);
            });
        }, 1000);
    });
} 