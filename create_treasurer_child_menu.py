#!/usr/bin/env python3
"""
Скрипт для создания дочернего меню казначея
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def create_treasurer_child_menu():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🔧 Создаем дочернее меню для казначея...")
        
        # ID родительского меню "ТДК/Заявки"
        parent_menu_id = 122
        
        # Получаем группу казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], 
            {'fields': ['id']})
        
        if not treasurer_group:
            print("❌ Группа казначея не найдена!")
            return
            
        treasurer_group_id = treasurer_group[0]['id']
        print(f"✅ ID группы казначея: {treasurer_group_id}")
        
        # Проверяем существует ли уже дочернее меню казначея
        existing_child = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [['&', ['parent_id', '=', parent_menu_id], ['action', 'ilike', '507']]], 
            {'fields': ['id', 'name', 'action']})
        
        if existing_child:
            print(f"✅ Дочернее меню казначея уже существует: ID {existing_child[0]['id']}")
            menu_id = existing_child[0]['id']
        else:
            print(f"🔧 Создаем новое дочернее меню казначея...")
            
            # Создаем дочернее меню
            menu_data = {
                'name': 'Заявки',
                'parent_id': parent_menu_id,
                'action': 'ir.actions.act_window,507',
                'groups_id': [(6, 0, [treasurer_group_id])],  # Только группа казначея
                'sequence': 1,  # Высший приоритет
                'active': True
            }
            
            menu_id = models.execute_kw(db, uid, password, 'ir.ui.menu', 'create', [menu_data])
            print(f"✅ Создано дочернее меню: ID {menu_id}")
        
        # Проверяем результат
        print(f"\n🔍 Проверяем созданное дочернее меню...")
        
        created_menu = models.execute_kw(db, uid, password, 'ir.ui.menu', 'read',
            [[menu_id]], {'fields': ['name', 'parent_id', 'action', 'groups_id', 'sequence', 'active']})
        
        if created_menu:
            menu = created_menu[0]
            print(f"✅ Название: {menu['name']}")
            print(f"✅ Родитель: {menu['parent_id'][1] if menu['parent_id'] else 'Нет'}")
            print(f"✅ Действие: {menu['action']}")
            print(f"✅ Приоритет: {menu['sequence']}")
            print(f"✅ Активно: {menu['active']}")
            
            if menu['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [menu['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                print(f"✅ Группы: {', '.join(group_names)}")
        
        # Финальная проверка: какие дочерние меню видит казначей
        print(f"\n🎯 ФИНАЛЬНАЯ ПРОВЕРКА дочерних меню для казначея:")
        
        child_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['parent_id', '=', parent_menu_id]]], 
            {'fields': ['id', 'name', 'action', 'groups_id', 'sequence'], 
             'order': 'sequence ASC, id ASC'})
        
        accessible_children = []
        
        for menu in child_menus:
            # Проверяем доступность казначею
            is_accessible = False
            if menu['groups_id']:
                groups = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [menu['groups_id']], {'fields': ['name']})
                group_names = [g['name'] for g in groups]
                is_accessible = 'Казначей' in group_names
            else:
                is_accessible = True  # Доступно всем
            
            action_info = "Нет действия"
            if menu['action']:
                action_parts = menu['action'].split(',')
                if len(action_parts) == 2:
                    action_info = f"action-{action_parts[1]}"
            
            accessibility = "✅ ДОСТУПНО" if is_accessible else "❌ НЕ ДОСТУПНО"
            
            print(f"  ID {menu['id']}: {menu['name']} → {action_info} | {accessibility}")
            
            if is_accessible:
                accessible_children.append(menu)
        
        print(f"\n🎯 ИТОГ:")
        print(f"   Дочерних меню доступных казначею: {len(accessible_children)}")
        
        if len(accessible_children) == 1:
            menu = accessible_children[0]
            action_parts = menu['action'].split(',') if menu['action'] else ['', 'None']
            action_id = action_parts[1] if len(action_parts) == 2 else 'None'
            
            if action_id == '507':
                print(f"   ✅ ОТЛИЧНО! Казначей видит только action-507")
                print(f"\n🎉 ПРОБЛЕМА РЕШЕНА!")
                print(f"📝 Теперь Ильзира должна:")
                print(f"   1. Очистить кэш браузера (Ctrl+Shift+R)")
                print(f"   2. Перелогиниться")
                print(f"   3. Нажать 'Заявки' должно открыть action-507!")
            else:
                print(f"   ⚠️  Меню ведет к action-{action_id}")
        else:
            print(f"   ⚠️  Казначей видит {len(accessible_children)} дочерних меню")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    create_treasurer_child_menu() 