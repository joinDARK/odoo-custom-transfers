odoo.define('amanat.sidebar', function (require) {
    "use strict";
    var core = require('web.core');
    var Widget = require('web.Widget');

    var Sidebar = Widget.extend({
        start: function () {
            var self = this;
            this.$toggle = $('.sidebar-toggle');
            this.$sidebar = $('.sidebar');
            this.$toggle.on('click', function () {
                self.$sidebar.toggleClass('active');
            });
        },
    });

    core.action_registry.add('amanat.sidebar', Sidebar);
    return Sidebar;
});