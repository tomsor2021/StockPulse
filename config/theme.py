"""浅色/深色主题配置"""
def get_theme_color(theme: str) -> dict:
    if theme == "深色":
        return {"up": "#F44336","down": "#4CAF50","flat": "#9E9E9E","bg": "#1E1E1E","card_bg": "#2D2D2D","text": "#FFFFFF","text_secondary": "#B0B0B0"}
    return {"up": "#D32F2F","down": "#2E7D32","flat": "#9E9E9E","bg": "#FFFFFF","card_bg": "#F5F5F5","text": "#212121","text_secondary": "#757575"}
def color_change(pct, colors):
    if pct is None: return colors["flat"]
    return colors["up"] if pct > 0 else (colors["down"] if pct < 0 else colors["flat"])
def arrow_change(pct):
    if pct is None: return "→"
    return "↑" if pct > 0 else ("↓" if pct < 0 else "→")
