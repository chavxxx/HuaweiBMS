"""Desktop Application Entry Point for Huawei EMS B1 Battery Manager.

Runs the local FastAPI/WebSocket server and hosts the React UI in a native desktop window
(via pywebview) across Windows, macOS, and Linux, with automatic fallback to system browser.
"""

import argparse
import logging
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("huawei_bms.desktop")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a network port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def find_available_port(start_port: int = 8000, host: str = "127.0.0.1") -> int:
    """Find next open port starting from start_port."""
    for p in range(start_port, start_port + 50):
        if not is_port_in_use(p, host):
            return p
    return start_port


def wait_for_server(url: str, timeout: float = 10.0) -> bool:
    """Wait for the backend server health check to respond with 200."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(f"{url}/api/health", headers={"User-Agent": "HuaweiBMSDesktop/1.0"})
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def run_uvicorn_server(host: str, port: int, server_ready_event: threading.Event):
    """Run Uvicorn FastAPI server in background thread."""
    import uvicorn
    from app.main import app

    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=False
    )
    server = uvicorn.Server(config)
    
    # Store server reference for shutdown
    global _uvicorn_server
    _uvicorn_server = server
    server_ready_event.set()
    server.run()


_uvicorn_server = None


def main():
    parser = argparse.ArgumentParser(description="Huawei EMS B1 Battery Manager Desktop Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--headless", "--no-gui", action="store_true", help="Run in headless server mode without desktop window")
    args = parser.parse_args()

    host = args.host
    port = args.port

    # Check if port is available; if not and port 8000 is taken by existing Huawei instance, check health
    if is_port_in_use(port, host):
        logger.info("Port %d is already in use. Checking if an existing Huawei BMS instance is responding...", port)
        app_url = f"http://{host}:{port}"
        if wait_for_server(app_url, timeout=1.5):
            logger.info("Existing Huawei BMS service found on port %d. Opening UI directly.", port)
            if not args.headless:
                try:
                    import webview
                    webview.create_window(
                        title="Huawei EMS B1 Battery Manager",
                        url=app_url,
                        width=1280,
                        height=840,
                        min_size=(960, 640),
                        background_color="#020617"
                    )
                    webview.start()
                    return
                except Exception as e:
                    logger.warning("Native webview unavailable (%s). Opening system browser...", e)
                    webbrowser.open(app_url)
                    return
            else:
                print(f"Huawei EMS B1 Battery Manager is already running on {app_url}")
                return
        else:
            # Port is occupied by another app; find an available port
            port = find_available_port(port + 1, host)
            logger.info("Selected alternate port %d", port)

    app_url = f"http://{host}:{port}"
    server_ready = threading.Event()

    # Start FastAPI server in background thread
    server_thread = threading.Thread(
        target=run_uvicorn_server,
        args=(host, port, server_ready),
        name="UvicornServerThread",
        daemon=True
    )
    server_thread.start()

    logger.info("Starting Huawei EMS B1 Battery Manager on %s ...", app_url)
    
    # Wait for server to become responsive
    if not wait_for_server(app_url, timeout=10.0):
        logger.error("Failed to start server within timeout. Exiting.")
        sys.exit(1)

    logger.info("Server is healthy and serving.")

    if args.headless:
        print(f"\n=========================================================")
        print(f" Huawei EMS B1 Battery Manager (Server Mode)")
        print(f" URL: {app_url}")
        print(f" Status: Active (Press Ctrl+C to stop)")
        print(f"=========================================================\n")
        try:
            while server_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Shutdown requested via KeyboardInterrupt.")
            sys.exit(0)
        return

    # Desktop GUI Window Mode
    gui_started = False
    try:
        import webview
        logger.info("Launching native desktop window via WebKit/Edge/WebView2...")
        window = webview.create_window(
            title="Huawei EMS B1 Battery Manager",
            url=app_url,
            width=1280,
            height=840,
            min_size=(960, 640),
            background_color="#020617",
            confirm_close=True
        )
        gui_started = True
        webview.start(debug=False)
        logger.info("Desktop window closed by user.")
    except Exception as e:
        logger.warning("Could not launch native webview (%s). Falling back to default web browser.", e)
        webbrowser.open(app_url)
        print(f"\n=========================================================")
        print(f" Huawei EMS B1 Battery Manager launched in default browser.")
        print(f" URL: {app_url}")
        print(f" Close this terminal window or press Ctrl+C to stop.")
        print(f"=========================================================\n")
        try:
            while server_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")

    # Graceful cleanup on desktop exit
    logger.info("Cleaning up serial resources before process termination...")
    try:
        from app.state import app_context
        app_context.telemetry_service.stop_polling()
        app_context.serial_client.disconnect()
    except Exception:
        pass


if __name__ == "__main__":
    main()
