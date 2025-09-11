#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрационный скрипт для тестирования триггера zayavka_num

ВНИМАНИЕ: Этот скрипт предназначен для демонстрации работы триггера.
Запускается из Odoo shell или как отдельный скрипт для тестирования.

Пример использования:
python3 odoo-bin shell -d your_database --addons-path=your_addons_path
>>> exec(open('/path/to/this/script.py').read())
"""

def test_zayavka_num_trigger():
    """
    Тестирует работу триггера zayavka_num
    """
    print("=== ТЕСТИРОВАНИЕ ТРИГГЕРА ZAYAVKA_NUM ===")
    
    # Получаем модель заявок
    Zayavka = env['amanat.zayavka']
    
    print("\n1. Создание новой заявки с номером...")
    # Создание новой заявки
    new_zayavka = Zayavka.create({
        'name': 'Тестовая заявка для триггера',
        'zayavka_num': '1',  # Устанавливаем номер 1
    })
    print(f"Создана заявка ID: {new_zayavka.id}")
    
    print("\n2. Изменение номера заявки с 1 на 2...")
    # Изменение номера заявки
    new_zayavka.write({
        'zayavka_num': '2'  # Изменяем на номер 2
    })
    
    print("\n3. Попытка изменить номер на тот же самый (не должно логироваться)...")
    # Попытка изменить на тот же номер (не должно сработать)
    new_zayavka.write({
        'zayavka_num': '2'  # Тот же номер
    })
    
    print("\n4. Изменение номера заявки с 2 на 3...")
    # Ещё одно изменение
    new_zayavka.write({
        'zayavka_num': '3'  # Изменяем на номер 3
    })
    
    print(f"\nИтоговый номер заявки: {new_zayavka.zayavka_num}")
    print("=== ТЕСТ ЗАВЕРШЁН ===")
    
    return new_zayavka

if __name__ == '__main__':
    # Этот блок выполнится только при запуске из Odoo shell
    try:
        test_zayavka_num_trigger()
    except NameError:
        print("Этот скрипт должен запускаться из Odoo shell с доступным объектом 'env'")
        print("Пример: python3 odoo-bin shell -d your_database")
        print(">>> exec(open('/path/to/test_zayavka_num_trigger.py').read())")

