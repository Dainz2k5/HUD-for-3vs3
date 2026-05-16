from app import create_app
import config

app = create_app()

if __name__ == '__main__':
    app.run(port=config.SERVER_PORT, debug=config.DEBUG_MODE)
