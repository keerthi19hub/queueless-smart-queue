import os
from app import app
from db import init_db

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print(f"=======================================================")
    print(f" QueueLess: Smart Queue Management System")
    print(f" Server running at: http://127.0.0.1:{port}")
    print(f" Admin Dashboard:   http://127.0.0.1:{port}/admin")
    print(f" Public Kiosk TV:   http://127.0.0.1:{port}/display")
    print(f"=======================================================")
    app.run(host="0.0.0.0", port=port, debug=True)
