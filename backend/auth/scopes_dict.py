scopes = {                              # Список прав в приложении
    'admin:all': 'Права админа',
    'user:all': 'Права пользователя',
}

default_scopes_users = [                # Влияет какие права будут доступны юзеру сразу после регистрации
    'user:all',
]

super_admin_scopes = [                  # Влияет какие права будут доступны супер админу, который создается в initial_data.py
    'admin:all',
    'user:all'
]
