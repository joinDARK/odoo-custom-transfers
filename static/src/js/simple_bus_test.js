/** @odoo-module **/

import { registry } from "@web/core/registry";

// Простой тестовый сервис для bus диагностики
const simpleBusTestService = {
    dependencies: ["bus_service", "notification"],
    
    start(env, { bus_service, notification }) {
        console.log("🧪 Simple Bus Test Service starting...");
        
        // Добавляем слушатель для ВСЕХ bus сообщений
        bus_service.addEventListener("notification", ({ detail: notifications }) => {
            console.log("🧪 SIMPLE BUS TEST: Received notifications:", notifications);
            
            for (const notification of notifications) {
                console.log("🧪 SIMPLE BUS TEST: Processing:", notification);
                
                // Проверяем все возможные форматы
                if (Array.isArray(notification)) {
                    console.log(`🧪 Array format: [${notification.join(", ")}]`);
                    // Ищем amanat в любом элементе массива
                    for (let i = 0; i < notification.length; i++) {
                        const item = notification[i];
                        if (typeof item === 'string' && item.includes('amanat')) {
                            console.log("🎯 Found amanat in array item:", item, "at index", i);
                        } else if (typeof item === 'object' && item && JSON.stringify(item).includes('amanat')) {
                            console.log("🎯 Found amanat in object:", item, "at index", i);
                        }
                    }
                } else if (typeof notification === 'object' && notification) {
                    console.log("🧪 Object format:", Object.keys(notification));
                    const jsonStr = JSON.stringify(notification);
                    if (jsonStr.includes('amanat')) {
                        console.log("🎯 Found amanat in object notification:", notification);
                    }
                }
            }
        });
        
        // Глобальные тестовые функции
        window.testBusSimple = () => {
            console.log("🧪 SIMPLE TEST: Testing bus reception...");
            notification.add("Простой тест Bus запущен! Смотрите консоль.", {
                type: "info",
                title: "Bus Тест"
            });
        };
        
        window.testCreateRecord = async () => {
            console.log("🧪 SIMPLE TEST: Creating test record...");
            try {
                const result = await env.services.rpc("/amanat/test_bus", {});
                console.log("🧪 SIMPLE TEST: RPC result:", result);
                notification.add("Тестовая запись создана! Смотрите консоль.", {
                    type: "success",
                    title: "Создание записи"
                });
            } catch (error) {
                console.error("🧪 SIMPLE TEST ERROR:", error);
                notification.add(`Ошибка: ${error.message}`, {
                    type: "danger",
                    title: "Ошибка теста"
                });
            }
        };
        
        console.log("🧪 Simple Bus Test Service started");
        console.log("🧪 Simple Bus Test functions registered:");
        console.log("🧪 - window.testBusSimple()");
        console.log("🧪 - window.testCreateRecord()");
        
        return {};
    }
};

// Регистрируем сервис
registry.category("services").add("simple_bus_test", simpleBusTestService);

console.log("🧪 Simple Bus Test Service registered"); 