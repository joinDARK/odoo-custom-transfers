/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

class ChatterToggleService {
    constructor() {
        this.chatterVisible = false; // Изменено: по умолчанию логи скрыты
        this.toggleButton = null;
        this.checkTimeout = null;
        this.lastUrl = location.href;
        this.mutationObserver = null;
        this.intervalId = null;
    }

    start() {
        this.initChatterToggle();
        this.setupObservers();
    }

    createToggleButton() {
        if (this.toggleButton) return;
        
        const navbar = document.querySelector('.o_main_navbar .o_menu_systray');
        if (!navbar) {
            console.log('Chatter Toggle: navbar не найден');
            return;
        }
        
        this.toggleButton = document.createElement('button');
        this.toggleButton.className = 'chatter-toggle-btn';
        // Устанавливаем иконку и заголовок в зависимости от текущего состояния
        if (this.chatterVisible) {
            this.toggleButton.innerHTML = '<i class="fa fa-eye-slash"></i>';
            this.toggleButton.title = 'Скрыть логи';
        } else {
            this.toggleButton.innerHTML = '<i class="fa fa-eye"></i>';
            this.toggleButton.title = 'Показать логи';
        }
        this.toggleButton.type = 'button';
        
        this.toggleButton.style.cssText = `
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
        
        this.toggleButton.addEventListener('click', () => this.toggleChatter());
        this.toggleButton.addEventListener('mouseenter', function() {
            this.style.color = '#495057';
            this.style.backgroundColor = 'rgba(0,0,0,0.05)';
        });
        this.toggleButton.addEventListener('mouseleave', () => {
            this.toggleButton.style.color = this.chatterVisible ? '#dc3545' : '#6c757d';
            this.toggleButton.style.backgroundColor = 'transparent';
        });
        
        // Устанавливаем правильный цвет при создании кнопки
        this.toggleButton.style.color = this.chatterVisible ? '#dc3545' : '#6c757d';
        
        navbar.insertBefore(this.toggleButton, navbar.firstChild);
        console.log('Chatter Toggle: кнопка создана и добавлена в navbar');
    }

    removeToggleButton() {
        if (this.toggleButton) {
            this.toggleButton.remove();
            this.toggleButton = null;
            console.log('Chatter Toggle: кнопка удалена');
        }
    }

    hideChatterElements() {
        const chatters = document.querySelectorAll('.o-mail-Chatter, .o-mail-ChatterContainer, .o-mail-Form-chatter');
        console.log('Chatter Toggle: скрываем чэттеры при инициализации:', chatters.length);
        chatters.forEach(chatter => {
            chatter.style.display = 'none';
        });
    }

    toggleChatter() {
        const chatters = document.querySelectorAll('.o-mail-Chatter, .o-mail-ChatterContainer, .o-mail-Form-chatter');
        console.log('Chatter Toggle: найдено чэттеров:', chatters.length);
        
        if (this.chatterVisible) {
            chatters.forEach(chatter => {
                chatter.style.display = 'none';
            });
            this.toggleButton.innerHTML = '<i class="fa fa-eye"></i>';
            this.toggleButton.title = 'Показать логи';
            this.toggleButton.style.color = '#6c757d';
            this.chatterVisible = false;
            console.log('Chatter Toggle: чэттеры скрыты');
        } else {
            chatters.forEach(chatter => {
                chatter.style.display = '';
            });
            this.toggleButton.innerHTML = '<i class="fa fa-eye-slash"></i>';
            this.toggleButton.title = 'Скрыть логи';
            this.toggleButton.style.color = '#dc3545';
            this.chatterVisible = true;
            console.log('Chatter Toggle: чэттеры показаны');
        }
    }

    checkIfFormWithChatter() {
        const hasForm = document.querySelector('.o_form_view');
        if (!hasForm) return false;
        
        const hasChatter = (
            document.querySelector('.o-mail-Chatter') || 
            document.querySelector('.o-mail-ChatterContainer') || 
            document.querySelector('.o-mail-Form-chatter') ||
            document.querySelector('[name="message_ids"]') ||
            document.querySelector('[name="message_follower_ids"]') ||
            document.querySelector('[name="activity_ids"]') ||
            document.querySelector('.oe_chatter') ||
            document.querySelector('.o_mail_thread') ||
            document.querySelector('.o_form_view .o-mail-Chatter')
        );
        
        return hasForm && hasChatter;
    }

    initChatterToggle() {
        if (this.checkIfFormWithChatter()) {
            console.log('Chatter Toggle: форма с чэттером найдена');
            this.createToggleButton();
            // Автоматически скрываем чаттеры при инициализации, если они должны быть скрыты
            if (!this.chatterVisible) {
                this.hideChatterElements();
            }
        } else {
            console.log('Chatter Toggle: форма с чэттером не найдена');
            this.removeToggleButton();
        }
    }

    debouncedCheck() {
        if (this.checkTimeout) clearTimeout(this.checkTimeout);
        this.checkTimeout = setTimeout(() => {
            if (this.checkIfFormWithChatter() && !this.toggleButton) {
                this.createToggleButton();
                // Скрываем чаттеры при создании кнопки, если они должны быть скрыты
                if (!this.chatterVisible) {
                    this.hideChatterElements();
                }
            } else if (!this.checkIfFormWithChatter() && this.toggleButton) {
                this.removeToggleButton();
            }
        }, 500);
    }

    setupObservers() {
        // Отслеживание изменений в DOM для SPA
        this.mutationObserver = new MutationObserver(() => {
            const url = location.href;
            if (url !== this.lastUrl) {
                this.lastUrl = url;
                setTimeout(() => this.initChatterToggle(), 500);
            }
        });
        this.mutationObserver.observe(document, { subtree: true, childList: true });
        
        // Проверка каждые 3 секунды
        this.intervalId = setInterval(() => this.debouncedCheck(), 3000);
    }

    destroy() {
        this.removeToggleButton();
        if (this.checkTimeout) {
            clearTimeout(this.checkTimeout);
        }
        if (this.mutationObserver) {
            this.mutationObserver.disconnect();
        }
        if (this.intervalId) {
            clearInterval(this.intervalId);
        }
    }
}

const chatterToggleService = {
    start() {
        const service = new ChatterToggleService();
        service.start();
        return service;
    },
};

registry.category("services").add("chatter_toggle", chatterToggleService); 