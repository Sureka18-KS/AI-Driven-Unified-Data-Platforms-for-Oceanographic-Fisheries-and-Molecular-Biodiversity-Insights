import os

with open('frontend/app.js', 'r', encoding='utf-8') as f:
    app_js = f.read()

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace <script type="text/babel" data-type="module" src="/app.js"></script>
# With <script type="text/babel" data-type="module">...content...</script>

target_script = '<script type="text/babel" data-type="module" src="/app.js"></script>'
if target_script in html:
    html = html.replace(target_script, f'<script type="text/babel" data-type="module">\n{app_js}\n</script>')
    with open('frontend/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("SUCCESS: Injected app.js into index.html inline!")
else:
    print("ERROR: Target script tag not found in index.html")
