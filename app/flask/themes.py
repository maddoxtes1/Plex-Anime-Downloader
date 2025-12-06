"""
Module de gestion des thèmes pour l'interface Flask
Contient les définitions CSS pour tous les thèmes disponibles
"""

THEMES = {
    "neon-cyberpunk": {
        "name": "Anime Neon Cyberpunk",
        "colors": {
            "bg_primary": "#0a0a0f",
            "bg_secondary": "#1a1a2e",
            "bg_card": "#0a0a0f",
            "accent_primary": "#00d4ff",
            "accent_secondary": "#ff006e",
            "accent_tertiary": "#ffbe0b",
            "text_primary": "#ffffff",
            "text_secondary": "#a0a0b0",
            "border": "#2a2a3e",
            "success": "#00ff88",
            "error": "#ff006e",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #0a0a0f;
                color: #ffffff;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #1a1a2e;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #2a2a3e;
                box-shadow: 0 0 20px rgba(0, 212, 255, 0.1);
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
                text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #a0a0b0;
            }
            header a {
                color: #ffffff;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #2a2a3e;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: rgba(0, 212, 255, 0.1);
                border-color: #00d4ff;
                box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #0a0a0f;
                border-radius: 14px;
                border: 1px solid #2a2a3e;
                padding: 18px 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 20px rgba(0, 212, 255, 0.05);
                transition: all 0.3s ease;
            }
            .card:hover {
                border-color: #00d4ff;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 212, 255, 0.1);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
            }
            p {
                font-size: 0.9rem;
                color: #a0a0b0;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #a0a0b0;
                border-bottom: 1px solid #2a2a3e;
            }
            tr:nth-child(even) td {
                background: #0a0a0f;
            }
            tr:nth-child(odd) td {
                background: #0f0f1a;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(0, 255, 136, 0.12);
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.35);
                box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(255, 0, 110, 0.15);
                color: #ff6ba3;
                border: 1px solid rgba(255, 0, 110, 0.3);
                box-shadow: 0 0 10px rgba(255, 0, 110, 0.2);
            }
            .msg.success {
                background: rgba(0, 255, 136, 0.12);
                color: #00ff88;
                border: 1px solid rgba(0, 255, 136, 0.3);
                box-shadow: 0 0 10px rgba(0, 255, 136, 0.2);
            }
            .empty {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #6b7280;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #a0a0b0;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #0a0a0f;
                border-radius: 8px;
                border: 1px solid #2a2a3e;
                color: #ffffff;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #00d4ff;
                box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #2a2a3e;
                background: #1a1a2e;
                color: #ffffff;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
            }
            button.btn.primary {
                border-color: #00d4ff;
                background: linear-gradient(135deg, #00d4ff, #ff006e);
                box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
            }
            button.btn.primary:hover {
                box-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
            }
            button.btn.danger {
                border-color: #ff006e;
                color: #ffffff;
                background: rgba(255, 0, 110, 0.2);
            }
            button.btn.danger:hover {
                background: rgba(255, 0, 110, 0.3);
                box-shadow: 0 0 20px rgba(255, 0, 110, 0.4);
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #1a1a2e;
                padding: 2px 4px;
                border-radius: 4px;
                color: #00d4ff;
            }
        """
    },
    "sakura-pastel": {
        "name": "Sakura Pastel",
        "colors": {
            "bg_primary": "#fef7f0",
            "bg_secondary": "#fff5e8",
            "bg_card": "#ffffff",
            "accent_primary": "#ff6b9d",
            "accent_secondary": "#c77dff",
            "accent_tertiary": "#4ecdc4",
            "text_primary": "#2d3748",
            "text_secondary": "#718096",
            "border": "#e2e8f0",
            "success": "#48bb78",
            "error": "#f56565",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: linear-gradient(135deg, #fef7f0 0%, #fff5e8 100%);
                color: #2d3748;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #ffffff;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #e2e8f0;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
                color: #ff6b9d;
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #718096;
            }
            header a {
                color: #2d3748;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #e2e8f0;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: #ff6b9d;
                color: #ffffff;
                border-color: #ff6b9d;
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #ffffff;
                border-radius: 16px;
                border: 1px solid #e2e8f0;
                padding: 18px 20px;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
                transition: all 0.3s ease;
            }
            .card:hover {
                box-shadow: 0 8px 24px rgba(255, 107, 157, 0.15);
                transform: translateY(-2px);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
                color: #c77dff;
            }
            p {
                font-size: 0.9rem;
                color: #718096;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #718096;
                border-bottom: 1px solid #e2e8f0;
            }
            tr:nth-child(even) td {
                background: #fef7f0;
            }
            tr:nth-child(odd) td {
                background: #ffffff;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(78, 205, 196, 0.15);
                color: #4ecdc4;
                border: 1px solid rgba(78, 205, 196, 0.3);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(245, 101, 101, 0.15);
                color: #f56565;
                border: 1px solid rgba(245, 101, 101, 0.3);
            }
            .msg.success {
                background: rgba(72, 187, 120, 0.15);
                color: #48bb78;
                border: 1px solid rgba(72, 187, 120, 0.3);
            }
            .empty {
                font-size: 0.85rem;
                color: #a0aec0;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #a0aec0;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #718096;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
                color: #2d3748;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #ff6b9d;
                box-shadow: 0 0 0 3px rgba(255, 107, 157, 0.1);
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #e2e8f0;
                background: #ffffff;
                color: #2d3748;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }
            button.btn.primary {
                border-color: #ff6b9d;
                background: linear-gradient(135deg, #ff6b9d, #c77dff);
                color: #ffffff;
            }
            button.btn.danger {
                border-color: #f56565;
                color: #ffffff;
                background: #f56565;
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #fef7f0;
                padding: 2px 4px;
                border-radius: 4px;
                color: #c77dff;
            }
        """
    },
    "dark-anime-classic": {
        "name": "Dark Anime Classic",
        "colors": {
            "bg_primary": "#1a1a1a",
            "bg_secondary": "#252525",
            "bg_card": "#1a1a1a",
            "accent_primary": "#e63946",
            "accent_secondary": "#f77f00",
            "accent_tertiary": "#06d6a0",
            "text_primary": "#f1faee",
            "text_secondary": "#a8dadc",
            "border": "#3a3a3a",
            "success": "#06d6a0",
            "error": "#e63946",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #1a1a1a;
                color: #f1faee;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #252525;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #3a3a3a;
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
                color: #e63946;
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #a8dadc;
            }
            header a {
                color: #f1faee;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #3a3a3a;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: #e63946;
                border-color: #e63946;
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #1a1a1a;
                border-radius: 14px;
                border: 1px solid #3a3a3a;
                padding: 18px 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
                color: #f77f00;
            }
            p {
                font-size: 0.9rem;
                color: #a8dadc;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #a8dadc;
                border-bottom: 1px solid #3a3a3a;
            }
            tr:nth-child(even) td {
                background: #1a1a1a;
            }
            tr:nth-child(odd) td {
                background: #202020;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(6, 214, 160, 0.12);
                color: #06d6a0;
                border: 1px solid rgba(6, 214, 160, 0.35);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(230, 57, 70, 0.15);
                color: #e63946;
                border: 1px solid rgba(230, 57, 70, 0.3);
            }
            .msg.success {
                background: rgba(6, 214, 160, 0.12);
                color: #06d6a0;
                border: 1px solid rgba(6, 214, 160, 0.3);
            }
            .empty {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #6b7280;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #a8dadc;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #1a1a1a;
                border-radius: 8px;
                border: 1px solid #3a3a3a;
                color: #f1faee;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #e63946;
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #3a3a3a;
                background: #252525;
                color: #f1faee;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                transform: translateY(-2px);
            }
            button.btn.primary {
                border-color: #e63946;
                background: linear-gradient(135deg, #e63946, #f77f00);
            }
            button.btn.danger {
                border-color: #e63946;
                color: #ffffff;
                background: #e63946;
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #252525;
                padding: 2px 4px;
                border-radius: 4px;
                color: #f77f00;
            }
        """
    },
    "ocean-breeze": {
        "name": "Ocean Breeze",
        "colors": {
            "bg_primary": "#0f1419",
            "bg_secondary": "#1a2332",
            "bg_card": "#0f1419",
            "accent_primary": "#00d9ff",
            "accent_secondary": "#4facfe",
            "accent_tertiary": "#00f2fe",
            "text_primary": "#e0f2fe",
            "text_secondary": "#94a3b8",
            "border": "#1e3a5f",
            "success": "#00f2fe",
            "error": "#ff6b6b",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
                color: #e0f2fe;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #1a2332;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #1e3a5f;
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
                color: #00d9ff;
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #94a3b8;
            }
            header a {
                color: #e0f2fe;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #1e3a5f;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: rgba(0, 217, 255, 0.1);
                border-color: #00d9ff;
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #0f1419;
                border-radius: 14px;
                border: 1px solid #1e3a5f;
                padding: 18px 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
                transition: all 0.3s ease;
            }
            .card:hover {
                border-color: #00d9ff;
                box-shadow: 0 20px 40px rgba(0, 217, 255, 0.1);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
                color: #4facfe;
            }
            p {
                font-size: 0.9rem;
                color: #94a3b8;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #94a3b8;
                border-bottom: 1px solid #1e3a5f;
            }
            tr:nth-child(even) td {
                background: #0f1419;
            }
            tr:nth-child(odd) td {
                background: #141a24;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(0, 242, 254, 0.12);
                color: #00f2fe;
                border: 1px solid rgba(0, 242, 254, 0.35);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(255, 107, 107, 0.15);
                color: #ff6b6b;
                border: 1px solid rgba(255, 107, 107, 0.3);
            }
            .msg.success {
                background: rgba(0, 242, 254, 0.12);
                color: #00f2fe;
                border: 1px solid rgba(0, 242, 254, 0.3);
            }
            .empty {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #6b7280;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #94a3b8;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #0f1419;
                border-radius: 8px;
                border: 1px solid #1e3a5f;
                color: #e0f2fe;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #00d9ff;
                box-shadow: 0 0 10px rgba(0, 217, 255, 0.3);
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #1e3a5f;
                background: #1a2332;
                color: #e0f2fe;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 217, 255, 0.3);
            }
            button.btn.primary {
                border-color: #00d9ff;
                background: linear-gradient(135deg, #00d9ff, #4facfe);
            }
            button.btn.danger {
                border-color: #ff6b6b;
                color: #ffffff;
                background: #ff6b6b;
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #1a2332;
                padding: 2px 4px;
                border-radius: 4px;
                color: #4facfe;
            }
        """
    },
    "fire-ice": {
        "name": "Fire & Ice",
        "colors": {
            "bg_primary": "#0d1117",
            "bg_secondary": "#161b22",
            "bg_card": "#0d1117",
            "accent_primary": "#ff6b35",
            "accent_secondary": "#00d4ff",
            "accent_tertiary": "#ff006e",
            "text_primary": "#f0f6fc",
            "text_secondary": "#8b949e",
            "border": "#30363d",
            "success": "#00d4ff",
            "error": "#ff6b35",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #0d1117;
                color: #f0f6fc;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #161b22;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #30363d;
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
                background: linear-gradient(135deg, #ff6b35, #00d4ff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #8b949e;
            }
            header a {
                color: #f0f6fc;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #30363d;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: linear-gradient(135deg, rgba(255, 107, 53, 0.1), rgba(0, 212, 255, 0.1));
                border-color: #ff6b35;
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #0d1117;
                border-radius: 14px;
                border: 1px solid #30363d;
                padding: 18px 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
                transition: all 0.3s ease;
            }
            .card:hover {
                border-color: #ff6b35;
                box-shadow: 0 20px 40px rgba(255, 107, 53, 0.1);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
                color: #00d4ff;
            }
            p {
                font-size: 0.9rem;
                color: #8b949e;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #8b949e;
                border-bottom: 1px solid #30363d;
            }
            tr:nth-child(even) td {
                background: #0d1117;
            }
            tr:nth-child(odd) td {
                background: #161b22;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(0, 212, 255, 0.12);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.35);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(255, 107, 53, 0.15);
                color: #ff6b35;
                border: 1px solid rgba(255, 107, 53, 0.3);
            }
            .msg.success {
                background: rgba(0, 212, 255, 0.12);
                color: #00d4ff;
                border: 1px solid rgba(0, 212, 255, 0.3);
            }
            .empty {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #6b7280;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #8b949e;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #0d1117;
                border-radius: 8px;
                border: 1px solid #30363d;
                color: #f0f6fc;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #ff6b35;
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #30363d;
                background: #161b22;
                color: #f0f6fc;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                transform: translateY(-2px);
            }
            button.btn.primary {
                border-color: #ff6b35;
                background: linear-gradient(135deg, #ff6b35, #00d4ff);
            }
            button.btn.danger {
                border-color: #ff6b35;
                color: #ffffff;
                background: #ff6b35;
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #161b22;
                padding: 2px 4px;
                border-radius: 4px;
                color: #ff6b35;
            }
        """
    },
    "minimalist-dark": {
        "name": "Minimalist Dark",
        "colors": {
            "bg_primary": "#000000",
            "bg_secondary": "#1c1c1e",
            "bg_card": "#000000",
            "accent_primary": "#007aff",
            "accent_secondary": "#34c759",
            "accent_tertiary": "#ff3b30",
            "text_primary": "#ffffff",
            "text_secondary": "#8e8e93",
            "border": "#38383a",
            "success": "#34c759",
            "error": "#ff3b30",
        },
        "css": """
            body {
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: #000000;
                color: #ffffff;
                margin: 0;
                min-height: 100vh;
            }
            header {
                background: #1c1c1e;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid #38383a;
            }
            header h1 {
                font-size: 1.1rem;
                margin: 0;
            }
            header .right {
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 0.8rem;
                color: #8e8e93;
            }
            header a {
                color: #ffffff;
                text-decoration: none;
                padding: 5px 8px;
                border-radius: 999px;
                border: 1px solid #38383a;
                transition: all 0.3s ease;
            }
            header a:hover {
                background: #38383a;
            }
            .wrapper {
                max-width: 900px;
                margin: 24px auto;
                padding: 0 16px 32px;
            }
            .card {
                background: #000000;
                border-radius: 14px;
                border: 1px solid #38383a;
                padding: 18px 20px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
            }
            h2 {
                font-size: 1rem;
                margin: 0 0 8px;
            }
            p {
                font-size: 0.9rem;
                color: #8e8e93;
                margin: 0 0 14px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
            }
            th, td {
                padding: 8px 6px;
                text-align: left;
            }
            th {
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: #8e8e93;
                border-bottom: 1px solid #38383a;
            }
            tr:nth-child(even) td {
                background: #000000;
            }
            tr:nth-child(odd) td {
                background: #1c1c1e;
            }
            .badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 999px;
                font-size: 0.75rem;
                background: rgba(52, 199, 89, 0.12);
                color: #34c759;
                border: 1px solid rgba(52, 199, 89, 0.35);
            }
            .messages {
                margin-bottom: 12px;
            }
            .msg {
                font-size: 0.8rem;
                padding: 6px 8px;
                border-radius: 8px;
                margin-bottom: 4px;
            }
            .msg.error {
                background: rgba(255, 59, 48, 0.15);
                color: #ff3b30;
                border: 1px solid rgba(255, 59, 48, 0.3);
            }
            .msg.success {
                background: rgba(52, 199, 89, 0.12);
                color: #34c759;
                border: 1px solid rgba(52, 199, 89, 0.3);
            }
            .empty {
                font-size: 0.85rem;
                color: #6b7280;
                margin-top: 4px;
            }
            .section-title {
                margin-top: 4px;
                margin-bottom: 4px;
            }
            .sub {
                font-size: 0.8rem;
                color: #6b7280;
                margin-bottom: 10px;
            }
            form.inline {
                display: inline;
            }
            label.small {
                font-size: 0.8rem;
                color: #8e8e93;
                margin-right: 6px;
            }
            input[type="text"],
            input[type="number"],
            input[type="password"],
            select {
                background: #000000;
                border-radius: 8px;
                border: 1px solid #38383a;
                color: #ffffff;
                padding: 4px 6px;
                font-size: 0.85rem;
                transition: all 0.3s ease;
            }
            input[type="text"]:focus,
            input[type="number"]:focus,
            input[type="password"]:focus,
            select:focus {
                outline: none;
                border-color: #007aff;
            }
            input.short {
                width: 70px;
            }
            input.medium {
                width: 140px;
            }
            button.btn {
                border-radius: 999px;
                border: 1px solid #38383a;
                background: #1c1c1e;
                color: #ffffff;
                padding: 4px 10px;
                font-size: 0.8rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            button.btn:hover {
                background: #38383a;
            }
            button.btn.primary {
                border-color: #007aff;
                background: #007aff;
            }
            button.btn.danger {
                border-color: #ff3b30;
                color: #ffffff;
                background: #ff3b30;
            }
            .mt-2 { margin-top: 8px; }
            .mt-3 { margin-top: 12px; }
            .mt-4 { margin-top: 16px; }
            .mb-2 { margin-bottom: 8px; }
            .mb-3 { margin-bottom: 12px; }
            code {
                font-size: 0.8rem;
                background: #1c1c1e;
                padding: 2px 4px;
                border-radius: 4px;
                color: #007aff;
            }
        """
    }
}


def hex_to_rgb(hex_color):
    """Convertit une couleur hex en RGB pour rgba()"""
    hex_color = hex_color.lstrip('#')
    return ','.join(str(int(hex_color[i:i+2], 16)) for i in (0, 2, 4))


def get_tabs_css(colors):
    """Retourne le CSS pour les onglets basé sur les couleurs du thème"""
    accent_rgb = hex_to_rgb(colors['accent_primary'])
    return f"""
        .tabs-container {{
            background: {colors['bg_secondary']};
            border-bottom: 2px solid {colors['border']};
            padding: 0;
            margin: 0;
            display: flex;
            gap: 0;
        }}
        .tab-button {{
            flex: 1;
            padding: 12px 16px;
            background: transparent;
            border: none;
            border-bottom: 3px solid transparent;
            color: {colors['text_secondary']};
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }}
        .tab-button:hover {{
            background: rgba({accent_rgb}, 0.05);
            color: {colors['text_primary']};
        }}
        .tab-button.active {{
            color: {colors['accent_primary']};
            border-bottom-color: {colors['accent_primary']};
            background: rgba({accent_rgb}, 0.1);
        }}
        .tab-content {{
            display: none;
            padding: 20px;
        }}
        .tab-content.active {{
            display: block;
        }}
        .log-viewer {{
            background: {colors['bg_card']};
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 12px;
            max-height: 600px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            line-height: 1.5;
            color: {colors['text_primary']};
        }}
        .log-line {{
            margin: 2px 0;
            word-wrap: break-word;
        }}
        .log-selector {{
            margin-bottom: 12px;
        }}
        .log-selector select {{
            width: 100%;
            max-width: 300px;
        }}
        .log-controls {{
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            align-items: center;
        }}
        .log-controls button {{
            padding: 6px 12px;
            font-size: 0.8rem;
        }}
        .log-auto-scroll {{
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .log-auto-scroll input[type="checkbox"] {{
            width: auto;
        }}
        .log-content-pre {{
            margin: 0;
            padding: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', monospace;
            font-size: 0.75rem;
            line-height: 1.6;
            color: {colors['text_primary']};
        }}
        .tabs-container-header {{
            display: flex;
            gap: 4px;
            margin-right: 12px;
            align-items: center;
            flex: 1;
            justify-content: flex-start;
        }}
        .tab-button-header {{
            flex: 1;
            padding: 6px 12px;
            background: transparent;
            border: 1px solid {colors['border']};
            border-radius: 6px;
            color: {colors['text_secondary']};
            font-size: 0.75rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            text-align: center;
            min-width: 0;
        }}
        .tab-button-header:hover {{
            background: rgba({accent_rgb}, 0.1);
            color: {colors['text_primary']};
            border-color: {colors['accent_primary']};
        }}
        .tab-button-header.active {{
            color: {colors['accent_primary']};
            border-color: {colors['accent_primary']};
            background: rgba({accent_rgb}, 0.15);
            box-shadow: 0 0 8px rgba({accent_rgb}, 0.3);
        }}
    """


def get_theme_css(theme_name):
    """Retourne le CSS pour un thème donné avec les styles d'onglets"""
    theme = THEMES.get(theme_name, THEMES["neon-cyberpunk"])
    base_css = theme["css"]
    tabs_css = get_tabs_css(theme["colors"])
    return base_css + tabs_css


def get_theme_colors(theme_name):
    """Retourne les couleurs pour un thème donné"""
    return THEMES.get(theme_name, THEMES["neon-cyberpunk"])["colors"]


def get_available_themes():
    """Retourne la liste de tous les thèmes disponibles"""
    return {key: theme["name"] for key, theme in THEMES.items()}


def get_login_page_css(theme_name):
    """Retourne le CSS adapté pour la page de connexion (access.html)"""
    theme = THEMES.get(theme_name, THEMES["neon-cyberpunk"])
    colors = theme["colors"]
    
    return f"""
        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: linear-gradient(135deg, {colors['bg_primary']} 0%, {colors['bg_secondary']} 100%);
            color: {colors['text_primary']};
            margin: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
        }}
        .card {{
            background: {colors['bg_card']};
            padding: 24px 28px;
            border-radius: 14px;
            border: 1px solid {colors['border']};
            box-shadow: 0 18px 35px rgba(0, 0, 0, 0.8);
            width: 100%;
            max-width: 380px;
        }}
        h1 {{
            margin: 0 0 4px;
            font-size: 1.3rem;
            color: {colors['accent_primary']};
        }}
        p {{
            margin: 0 0 16px;
            font-size: 0.9rem;
            color: {colors['text_secondary']};
        }}
        label {{
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: {colors['text_primary']};
        }}
        input[type="password"] {{
            width: 100%;
            padding: 8px 10px;
            border-radius: 8px;
            border: 1px solid {colors['border']};
            background: {colors['bg_card']};
            color: {colors['text_primary']};
            font-size: 0.9rem;
            margin-bottom: 12px;
            transition: all 0.3s ease;
        }}
        input[type="password"]:focus {{
            outline: none;
            border-color: {colors['accent_primary']};
            box-shadow: 0 0 10px rgba(0, 212, 255, 0.3);
        }}
        button {{
            width: 100%;
            padding: 9px 12px;
            border-radius: 8px;
            border: none;
            background: linear-gradient(135deg, {colors['accent_primary']}, {colors['accent_secondary']});
            color: white;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        button:hover {{
            filter: brightness(1.1);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.3);
        }}
        .messages {{
            margin-bottom: 10px;
        }}
        .msg {{
            font-size: 0.8rem;
            padding: 6px 8px;
            border-radius: 8px;
            margin-bottom: 4px;
        }}
        .msg.error {{
            background: rgba(255, 0, 110, 0.15);
            color: {colors['error']};
            border: 1px solid rgba(255, 0, 110, 0.3);
        }}
        .msg.success {{
            background: rgba(0, 255, 136, 0.12);
            color: {colors['success']};
            border: 1px solid rgba(0, 255, 136, 0.3);
        }}
        .hint {{
            font-size: 0.75rem;
            color: {colors['text_secondary']};
            margin-top: 4px;
        }}
        code {{
            font-size: 0.8rem;
            background: {colors['bg_secondary']};
            padding: 2px 4px;
            border-radius: 4px;
            color: {colors['accent_primary']};
        }}
    """

