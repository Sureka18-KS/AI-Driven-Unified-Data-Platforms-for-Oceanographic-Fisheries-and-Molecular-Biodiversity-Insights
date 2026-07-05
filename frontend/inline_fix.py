import os

def inline_react_app():
    with open('app.js', 'r', encoding='utf-8') as f:
        app_content = f.read()

    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()

    # Make data.js NOT use text/babel
    html = html.replace('<script type="text/babel" src="data.js"></script>', '<script src="data.js"></script>')

    # Inline app.js
    inline_script = f'<script type="text/babel">\n{app_content}\n</script>'
    html = html.replace('<script type="text/babel" src="app.js"></script>', inline_script)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("Injection successful.")

if __name__ == "__main__":
    inline_react_app()
