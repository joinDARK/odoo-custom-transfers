# Улучшения Search View для сохранения состояния

## Дополнительные настройки XML для лучшего UX

### 1. Расширенные фильтры по умолчанию

Добавьте в actions контекст с `search_default_` для автоматического применения фильтров:

```xml
<!-- В файле views/zayavka_views.xml -->
<record id="zayavka_action_with_defaults" model="ir.actions.act_window">
    <field name="name">Заявки с сохранением</field>
    <field name="res_model">amanat.zayavka</field>
    <field name="view_mode">list,form</field>
    <field name="context">{
        'search_default_filter_active_zayavkas': 1,
        'search_default_group_by_status': 1,
        'search_default_this_month': 1
    }</field>
</record>
```

### 2. Улучшенные поля поиска с фильтрами домена

```xml
<search string="Улучшенный поиск заявок">
    <!-- Поиск с диапазонами дат -->
    <field name="date_placement" string="Дата размещения"
           filter_domain="[('date_placement','&gt;=',self),('date_placement','&lt;=',self)]" />
           
    <!-- Поиск по связанным полям -->
    <field name="contragent_id" string="Контрагент"
           filter_domain="[('contragent_id.name','ilike',self)]" />
           
    <!-- Поиск по сумме с операторами -->
    <field name="amount" string="Сумма"
           filter_domain="[('amount','&gt;=',self)]" />
           
    <!-- Поиск с автокомплитом -->
    <field name="client_id" string="Клиент"
           options="{'limit': 10, 'search_limit': 20}" />
</search>
```

### 3. Интеллектуальные фильтры

```xml
<search string="Интеллектуальный поиск">
    <!-- Группа быстрых фильтров -->
    <separator/>
    <filter name="today" string="Сегодня"
            domain="[('date_placement','=',context_today())]" />
    <filter name="this_week" string="На этой неделе"
            domain="[('date_placement','&gt;=',((context_today()-datetime.timedelta(days=context_today().weekday())).strftime('%Y-%m-%d')))]" />
    <filter name="this_month" string="В этом месяце"
            domain="[('date_placement','&gt;=',((context_today().replace(day=1)).strftime('%Y-%m-%d')))]" />
    
    <!-- Фильтры по статусам с цветовой кодировкой -->
    <separator/>
    <filter name="status_new" string="🆕 Новые"
            domain="[('status','in',['1_no_chat','2_in_chat'])]" />
    <filter name="status_work" string="⚙️ В работе"
            domain="[('status','in',['3_in_work','4_docs_ready'])]" />
    <filter name="status_done" string="✅ Завершенные"
            domain="[('status','in',['21','22'])]" />
            
    <!-- Фильтры по суммам -->
    <separator/>
    <filter name="amount_small" string="До 1M"
            domain="[('amount','&lt;',1000000)]" />
    <filter name="amount_medium" string="1M-10M"
            domain="[('amount','&gt;=',1000000),('amount','&lt;',10000000)]" />
    <filter name="amount_large" string="Свыше 10M"
            domain="[('amount','&gt;=',10000000)]" />
</search>
```

### 4. Умная группировка

```xml
<search string="Умная группировка">
    <!-- Стандартные группировки -->
    <group expand="0" string="Группировать по">
        <filter name="group_by_status" string="Статус"
                context="{'group_by':'status'}" />
        <filter name="group_by_contragent" string="Контрагент"
                context="{'group_by':'contragent_id'}" />
        <filter name="group_by_agent" string="Агент"
                context="{'group_by':'agent_id'}" />
                
        <!-- Группировка по периодам -->
        <separator/>
        <filter name="group_by_day" string="По дням"
                context="{'group_by':'date_placement:day'}" />
        <filter name="group_by_week" string="По неделям"
                context="{'group_by':'date_placement:week'}" />
        <filter name="group_by_month" string="По месяцам"
                context="{'group_by':'date_placement:month'}" />
        <filter name="group_by_quarter" string="По кварталам"
                context="{'group_by':'date_placement:quarter'}" />
                
        <!-- Группировка по диапазонам -->
        <separator/>
        <filter name="group_by_amount_range" string="По сумме"
                context="{'group_by':'amount_range'}" />
    </group>
</search>
```

### 5. Сохраненные поиски (Favorites) по умолчанию

```xml
<!-- Добавление предустановленных избранных фильтров -->
<record id="zayavka_filter_my_active" model="ir.filters">
    <field name="name">Мои активные заявки</field>
    <field name="model_id">amanat.zayavka</field>
    <field name="user_id" eval="False"/>
    <field name="domain">[('agent_id','=',uid),('status','not in',['21','22'])]</field>
    <field name="context">{'group_by':['status']}</field>
    <field name="is_default" eval="True"/>
</record>

<record id="zayavka_filter_high_priority" model="ir.filters">
    <field name="name">Высокий приоритет</field>
    <field name="model_id">amanat.zayavka</field>
    <field name="user_id" eval="False"/>
    <field name="domain">[('amount','&gt;=',5000000),('status','in',['3_in_work','4_docs_ready'])]</field>
    <field name="context">{'group_by':['contragent_id']}</field>
</record>
```

### 6. Контекстно-зависимые поиски

```xml
<!-- Разные search view для разных контекстов -->
<record id="zayavka_search_manager" model="ir.ui.view">
    <field name="name">zayavka.search.manager</field>
    <field name="model">amanat.zayavka</field>
    <field name="groups_id" eval="[(4, ref('group_amanat_manager'))]"/>
    <field name="arch" type="xml">
        <search string="Поиск для менеджеров">
            <!-- Расширенные поля для менеджеров -->
            <field name="profit" string="Прибыль" />
            <field name="commission" string="Комиссия" />
            
            <!-- Специальные фильтры для менеджеров -->
            <filter name="high_profit" string="Высокая прибыль"
                    domain="[('profit','&gt;=',100000)]" />
                    
            <!-- Группировка по прибыльности -->
            <group expand="1" string="Аналитика">
                <filter name="group_by_profit_range" string="По прибыли"
                        context="{'group_by':'profit_range'}" />
            </group>
        </search>
    </field>
</record>
```

### 7. Интеграция с новым функционалом сохранения

```xml
<!-- Action с улучшенным контекстом -->
<record id="zayavka_action_persistent" model="ir.actions.act_window">
    <field name="name">Заявки (с сохранением поиска)</field>
    <field name="res_model">amanat.zayavka</field>
    <field name="view_mode">list,form</field>
    <field name="search_view_id" ref="zayavka_search_view"/>
    <field name="context">{
        'default_status': '1_no_chat',
        'search_default_filter_active_zayavkas': 1,
        'amanat_search_persistence_enabled': True,
        'amanat_search_restore_on_load': True
    }</field>
</record>
```

## Дополнительные возможности

### 1. CSS стили для лучшего UX

Создайте файл `static/src/css/search_enhancements.css`:

```css
/* Подсветка активных фильтров */
.o_searchview .o_searchview_facet {
    background-color: #e3f2fd;
    border: 1px solid #2196f3;
}

/* Анимация при сохранении */
.amanat_search_saving {
    opacity: 0.7;
    transition: opacity 0.3s;
}

/* Индикатор сохраненного состояния */
.amanat_search_restored::before {
    content: "💾 ";
    color: #4caf50;
    font-weight: bold;
}
```

### 2. Уведомления пользователю

Добавьте в основной JavaScript модуль:

```javascript
// Показать уведомление о сохранении
showSaveNotification(modelName) {
    this.env.services.notification.add(
        `Состояние поиска сохранено для ${modelName}`,
        { type: 'success', sticky: false }
    );
}

// Показать уведомление о восстановлении
showRestoreNotification(modelName, itemsCount) {
    this.env.services.notification.add(
        `Восстановлено ${itemsCount} фильтров для ${modelName}`,
        { type: 'info', sticky: false }
    );
}
```

### 3. Кастомные виджеты для поиска

```xml
<!-- Виджет для поиска по диапазону дат -->
<field name="date_range" string="Период"
       widget="daterange" 
       options="{'related_start_date': 'date_placement', 'related_end_date': 'date_completion'}" />

<!-- Виджет множественного выбора -->
<field name="status" string="Статус"
       widget="many2many_checkboxes" />

<!-- Виджет слайдера для сумм -->
<field name="amount" string="Сумма"
       widget="float_range" 
       options="{'min': 0, 'max': 50000000, 'step': 100000}" />
```

## Результат

После внедрения всех улучшений пользователи получат:

✅ **Автоматическое сохранение** всех настроек поиска
✅ **Интуитивные фильтры** с эмодзи и цветовой кодировкой  
✅ **Быстрые переходы** между часто используемыми состояниями
✅ **Контекстно-зависимые** возможности поиска
✅ **Визуальную обратную связь** о сохранении и восстановлении
✅ **Гибкие настройки** под разные роли пользователей


