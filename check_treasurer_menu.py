#!/usr/bin/env python3
"""
Скрипт для проверки меню казначея
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def check_treasurer_menu():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🔍 Проверяем меню казначея...")
        
        # Получаем группу казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], 
            {'fields': ['id']})
        
        if not treasurer_group:
            print("❌ Группа казначея не найдена!")
            return
            
        treasurer_group_id = treasurer_group[0]['id']
        print(f"✅ ID группы казначея: {treasurer_group_id}")
        
        # Ищем ВСЕ меню "Заявки" доступные казначею
        print(f"\n📋 ПОИСК ВСЕХ МЕНЮ 'ЗАЯВКИ' ДЛЯ КАЗНАЧЕЯ:")
        
        # Поиск по названию "Заявки"
        zayavka_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['name', '=', 'Заявки']]], 
            {'fields': ['id', 'name', 'action', 'parent_id', 'groups_id', 'sequence'], 
             'order': 'sequence ASC, id ASC'})
        
        print(f"Найдено {len(zayavka_menus)} меню с названием 'Заявки':")
        
        treasurer_accessible = []
        
        for menu in zayavka_menus:
            # Проверяем доступно ли казначею
            is_accessible = False
            groups_info = "Все пользователи"
            
            if menu['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [menu['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                groups_info = ", ".join(group_names)
                
                # Доступно если казначей в списке групп
                is_accessible = 'Казначей' in group_names
            else:
                # Доступно всем если нет ограничений
                is_accessible = True
            
            action_info = "Нет действия"
            action_id = None
            if menu['action']:
                action_parts = menu['action'].split(',')
                if len(action_parts) == 2:
                    action_id = action_parts[1]
                    action_info = f"action-{action_id}"
            
            parent_info = menu['parent_id'][1] if menu['parent_id'] else "Корень"
            accessibility = "✅ ДОСТУПНО КАЗНАЧЕЮ" if is_accessible else "❌ НЕ ДОСТУПНО"
            
            print(f"\n  ID {menu['id']}: {menu['name']}")
            print(f"    Родитель: {parent_info}")
            print(f"    Действие: {action_info}")
            print(f"    Приоритет: {menu['sequence']}")
            print(f"    Группы: {groups_info}")
            print(f"    {accessibility}")
            
            if is_accessible:
                treasurer_accessible.append({
                    'menu': menu,
                    'action_id': action_id
                })
                
                # Отмечаем проблемные
                if action_id == '195':
                    print(f"    🚨 ПРОБЛЕМА: Это неправильное действие!")
                elif action_id == '507':
                    print(f"    ✅ ОТЛИЧНО: Это правильное действие казначея!")
        
        # Анализ доступных меню
        print(f"\n🎯 АНАЛИЗ ДОСТУПНЫХ КАЗНАЧЕЮ МЕНЮ:")
        print(f"   Всего меню 'Заявки': {len(zayavka_menus)}")
        print(f"   Доступных казначею: {len(treasurer_accessible)}")
        
        if len(treasurer_accessible) > 1:
            print(f"\n⚠️  ПРОБЛЕМА: Казначей видит {len(treasurer_accessible)} меню 'Заявки'!")
            print(f"   Odoo выберет первое по приоритету:")
            
            # Сортируем по приоритету
            sorted_accessible = sorted(treasurer_accessible, 
                                     key=lambda x: (x['menu']['sequence'] or 999, x['menu']['id']))
            
            for i, item in enumerate(sorted_accessible, 1):
                menu = item['menu']
                action_id = item['action_id']
                status = "🥇 ПЕРВОЕ (откроется по умолчанию)" if i == 1 else f"#{i}"
                
                print(f"   {status}: ID {menu['id']} → action-{action_id}")
                
                if i == 1:
                    if action_id == '195':
                        print(f"       ❌ ПОЭТОМУ ОТКРЫВАЕТСЯ action-195!")
                        print(f"       🔧 НУЖНО: Исправить приоритеты или скрыть это меню")
                    elif action_id == '507':
                        print(f"       ✅ Правильно! Открывается action-507")
                        
        elif len(treasurer_accessible) == 1:
            item = treasurer_accessible[0]
            action_id = item['action_id']
            
            if action_id == '507':
                print(f"   ✅ ОТЛИЧНО! Казначей видит только правильное меню action-507")
            elif action_id == '195':
                print(f"   ❌ ПРОБЛЕМА! Единственное меню ведет к action-195")
            else:
                print(f"   ⚠️  Единственное меню ведет к action-{action_id}")
        else:
            print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Казначей не видит ни одного меню!")
        
        # Рекомендации по исправлению
        print(f"\n💡 ПЛАН ИСПРАВЛЕНИЯ:")
        
        problem_menus = [item for item in treasurer_accessible 
                        if item['action_id'] == '195']
        
        if problem_menus:
            print(f"   1. Скрыть проблемные меню от казначея:")
            for item in problem_menus:
                menu = item['menu']
                print(f"      - Меню ID {menu['id']}: удалить группу 'Казначей'")
                
        good_menus = [item for item in treasurer_accessible 
                     if item['action_id'] == '507']
        
        if good_menus:
            print(f"   2. Убедиться что правильное меню имеет приоритет 1:")
            for item in good_menus:
                menu = item['menu']
                current_seq = menu['sequence'] or 999
                print(f"      - Меню ID {menu['id']}: текущий приоритет {current_seq}")
        else:
            print(f"   2. СОЗДАТЬ правильное меню для казначея с action-507")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    check_treasurer_menu() 