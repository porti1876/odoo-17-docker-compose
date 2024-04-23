# -*- coding: utf-8 -*-
{
    'name': "Saas sv",

    'summary': """
     """,

    'description': """
        Creacion de droplets con sus respectivas instancias
    """,

    'author': "Rocketters",
    'website': "https://rocketters.com/",

   
    'category': 'Server',
     'version': '16.01',
    'license': 'LGPL-3',
  
    'depends': ['base','mail'],

    
    'data': [
        'security/ir.model.access.csv',
        
        
        'data/cron.xml',
        'wizard/add_sh_keyge.xml',
        'wizard/delete_keys.xml',
        'wizard/add_project.xml',
        'wizard/del_projects.xml',  
        
        'wizard/copy_file_inst.xml',
        'wizard/creat_user_psql.xml',
        'wizard/generador_pwd.xml',
         
     
        'views/droplet.xml',
       
        'views/view_category.xml',
        'views/view_client.xml',
       
        'views/instancias.xml',
        'views/plan.xml',
        #'views/templates.xml',
         'views/res_company.xml',
        'views/menuitems.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
   
    
}
