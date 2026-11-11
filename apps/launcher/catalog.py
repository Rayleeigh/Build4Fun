"""Fixed launch targets. Browser requests cannot supply Compose paths or commands."""
APPS = {
    'build4fun': {'title': 'Build4Fun', 'description': 'Build services. Connect networks. Learn Docker.', 'accent': '#0000B4', 'port_env': 'B4F_HTTP_PORT', 'port': 8080,
                  'images': {'app': ''}},
    'code4fun': {'title': 'Code4Fun', 'description': 'Start with HTML. Build your first live dashboard.', 'accent': '#00C400', 'port_env': 'C4F_HTTP_PORT', 'port': 8090,
                 'images': {'workspace': 'code4fun-workspace', 'api': 'code4fun-api'}},
    'crack4fun': {'title': 'Crack4Fun', 'description': 'Follow the clues. Find the flags.', 'accent': '#C40000', 'port_env': 'CRACK_HTTP_PORT', 'port': 8100,
                  'images': {'workspace': 'crack4fun-workspace', 'filesystem': 'crack4fun-sandbox', 'forensics': 'crack4fun-sandbox', 'network': 'crack4fun-sandbox', 'web-terminal': 'crack4fun-sandbox', 'portal': 'crack4fun-portal'}}
}
