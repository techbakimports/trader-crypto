from src.config import load_config
from src.scanner import run

if __name__ == "__main__":
    cfg = load_config()
    run(cfg)
