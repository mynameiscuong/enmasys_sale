# -*- coding: utf-8 -*-
{
    'name': "Enmasys Sale",
    'summary': """Enmasys Sale""",
    'description': """""",
    'author': 'Enmasys',
    'company': 'Enmasys',
    'maintainer': 'Enmasys',
    'website': 'https://enmasys.com/',
    'category': 'Reporting',
    'version': '17.0.1.0.1',
    'license': 'AGPL-3',
    'sequence': 110,
    'depends': ['base', 'sale','purchase_request',],
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',

        # views
        'views/sale_order_view.xml',
        'views/year_difference_days.xml',
        'views/business_plan_views.xml',
        'views/sale_target_views.xml',
        'views/crm_team_inherit_views.xml',
        'views/inherit_res_partner_views.xml',
        'views/inherit_hr_employee_views.xml',

        # report
        'report/report_quotation.xml',
        'report/report_quotation_template.xml',
        'report/profit_loss_report_views.xml',
        'report/report.xml',
        'report/commission_performance_report_views.xml',
        'report/commission_performance_data_report_views.xml',

        # wizard
        'wizard/sale_revenue_report.xml',
        # 'views/production_inventory.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False
}
