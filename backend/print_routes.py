from app import create_app

app = create_app()
with app.app_context():
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if 'alerts' in rule.rule:
            print(f'{rule.rule} supports methods: {sorted(rule.methods)}')