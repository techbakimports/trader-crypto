from src.config import load_news_config
from src.news_scanner import run

if __name__ == "__main__":
    cfg = load_news_config()
    run(cfg)
