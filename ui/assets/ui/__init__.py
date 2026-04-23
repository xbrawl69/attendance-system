python -c "
folders = ['ui', 'database', 'core', 'utils']
for f in folders:
    open(f + '/__init__.py', 'w').close()
print('All __init__.py files created.')
"