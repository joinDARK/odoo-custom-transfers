#!/usr/bin/env python3
"""
Окончательное исправление меню казначея
"""

import xmlrpc.client

# Настройки подключения к Odoo
url = 'http://localhost:8069'
db = 'mydb'
username = 'admin'
password = 'admin'

def fix_menu_final():
    try:
        # Подключение к Odoo
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Ошибка аутентификации")
            return
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        print("🔧 ОКОНЧАТЕЛЬНОЕ ИСПРАВЛЕНИЕ МЕНЮ...")
        
        # Получаем ID группы казначея
        treasurer_group = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
            [[['name', '=', 'Казначей']]], 
            {'fields': ['id']})
        
        if not treasurer_group:
            print("❌ Группа казначея не найдена!")
            return
            
        treasurer_group_id = treasurer_group[0]['id']
        print(f"✅ ID группы казначея: {treasurer_group_id}")
        
        # ШАГ 1: Убираем казначея из меню ID 138 (action-195)
        print(f"\n🔧 ШАГ 1: Убираем казначея из проблемного меню ID 138...")
        
        menu_138 = models.execute_kw(db, uid, password, 'ir.ui.menu', 'read',
            [[138]], {'fields': ['groups_id']})
        
        if menu_138:
            current_groups = menu_138[0]['groups_id']
            print(f"   Текущие группы меню 138: {current_groups}")
            
            # Убираем казначея из групп
            if treasurer_group_id in current_groups:
                new_groups = [gid for gid in current_groups if gid != treasurer_group_id]
                
                models.execute_kw(db, uid, password, 'ir.ui.menu', 'write',
                    [[138], {'groups_id': [(6, 0, new_groups)]}])
                
                print(f"   ✅ Казначей удален из меню 138")
            else:
                print(f"   ℹ️  Казначея уже нет в меню 138")
        
        # ШАГ 2: Создаем новое дочернее меню для казначея
        print(f"\n🔧 ШАГ 2: Создаем дочернее меню казначея с action-507...")
        
        # Удаляем старые попытки создания (если есть)
        old_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search',
            [['&', '&', ['parent_id', '=', 122], ['name', '=', 'Заявки'], ['groups_id', 'in', [treasurer_group_id]]]])
        
        if old_menus:
            models.execute_kw(db, uid, password, 'ir.ui.menu', 'unlink', [old_menus])
            print(f"   Удалены старые меню казначея: {old_menus}")
        
        # Создаем новое меню
        menu_data = {
            'name': 'Заявки',
            'parent_id': 122,  # ТДК/Заявки
            'action': 'ir.actions.act_window,507',  # action-507 казначея
            'groups_id': [(6, 0, [treasurer_group_id])],  # Только казначей
            'sequence': 1,  # Высший приоритет
            'active': True
        }
        
        new_menu_id = models.execute_kw(db, uid, password, 'ir.ui.menu', 'create', [menu_data])
        print(f"   ✅ Создано новое меню казначея: ID {new_menu_id}")
        
        # ШАГ 3: Проверяем результат
        print(f"\n🔍 ШАГ 3: Проверяем финальный результат...")
        
        # Проверяем все дочерние меню ID 122
        child_menus = models.execute_kw(db, uid, password, 'ir.ui.menu', 'search_read',
            [[['parent_id', '=', 122]]], 
            {'fields': ['id', 'name', 'action', 'groups_id', 'sequence'], 
             'order': 'sequence ASC, id ASC'})
        
        treasurer_accessible = []
        
        print(f"Дочерние меню под 'ТДК/Заявки':")
        
        for menu in child_menus:
            # Проверяем доступность казначею
            is_accessible = False
            if menu['groups_id']:
                is_accessible = treasurer_group_id in menu['groups_id']
            else:
                is_accessible = True  # Доступно всем
            
            action_info = menu['action'] or 'Нет действия'
            accessibility = "✅ ДОСТУПНО КАЗНАЧЕЮ" if is_accessible else "❌ НЕ ДОСТУПНО"
            
            print(f"  ID {menu['id']}: {menu['name']} → {action_info}")
            print(f"    Приоритет: {menu['sequence']} | {accessibility}")
            
            if is_accessible:
                treasurer_accessible.append(menu)
        
        # Финальный анализ
        print(f"\n🎯 ФИНАЛЬНЫЙ АНАЛИЗ:")
        print(f"   Дочерних меню доступных казначею: {len(treasurer_accessible)}")
        
        if len(treasurer_accessible) == 1:
            menu = treasurer_accessible[0]
            action_parts = menu['action'].split(',') if menu['action'] else ['', 'None']
            action_id = action_parts[1] if len(action_parts) == 2 else 'None'
            
            if action_id == '507':
                print(f"   🎉 УСПЕХ! Казначей видит только action-507")
                print(f"\n✅ ПРОБЛЕМА РЕШЕНА!")
                print(f"📋 Теперь Ильзира должна:")
                print(f"   1. ПОЛНОСТЬЮ закрыть браузер")
                print(f"   2. Открыть браузер заново")
                print(f"   3. Залогиниться")
                print(f"   4. Нажать 'Заявки' → должен открыться action-507!")
            else:
                print(f"   ⚠️  Меню ведет к action-{action_id} (ожидался 507)")
        elif len(treasurer_accessible) > 1:
            print(f"   ⚠️  ПРОБЛЕМА: Казначей видит {len(treasurer_accessible)} меню")
            print(f"   Odoo откроет первое по приоритету:")
            
            sorted_menus = sorted(treasurer_accessible, key=lambda x: (x['sequence'] or 999, x['id']))
            first_menu = sorted_menus[0]
            action_parts = first_menu['action'].split(',') if first_menu['action'] else ['', 'None']
            action_id = action_parts[1] if len(action_parts) == 2 else 'None'
            
            print(f"   Первое меню: ID {first_menu['id']} → action-{action_id}")
        else:
            print(f"   ❌ КРИТИЧЕСКАЯ ОШИБКА: Казначей НЕ видит ни одного меню!")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    fix_menu_final() 