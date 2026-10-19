"""Desktop Application Entry Point for Huawei EMS B1 Battery Manager.

Runs the local FastAPI/WebSocket server and hosts the React UI in a native desktop window
(via pywebview) across Windows, macOS, and Linux, with automatic fallback to system browser.
"""

import argparse
import io
import logging
import multiprocessing
import os
import socket
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional

# Ensure parent backend directory is in sys.path when running from source
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Setup robust log directory for standalone/frozen environments
def get_log_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        log_dir = Path(base) / "HuaweiEMSManager" / "logs"
    else:
        log_dir = Path.home() / ".huawei_bms_manager" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir

LOG_DIR = get_log_dir()
LOG_FILE = LOG_DIR / "desktop.log"


class SafeLogWriter:
    """Thread-safe stream replacement for sys.stdout/sys.stderr in windowed (console=False) mode."""
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        if not s:
            return 0
        try:
            with self._lock:
                with open(self.log_path, "a", encoding="utf-8", errors="replace") as f:
                    f.write(s)
        except Exception:
            pass
        return len(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        pass

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False


# Determine if running in a windowed GUI mode without a console
is_windowed = sys.stdout is None or sys.stderr is None

if sys.stdout is None:
    sys.stdout = SafeLogWriter(LOG_FILE)
if sys.stderr is None:
    sys.stderr = SafeLogWriter(LOG_FILE)

# Setup logging: FileHandler always logs everything; StreamHandler only if an interactive console exists
log_handlers = [logging.FileHandler(str(LOG_FILE), encoding="utf-8")]
if not is_windowed and hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
    log_handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=log_handlers
)
logger = logging.getLogger("huawei_bms.desktop")


def show_error_dialog(title: str, message: str):
    """Display a native message box for critical errors so they are never silent."""
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR | MB_OK
        elif sys.platform == "darwin":
            import subprocess
            subprocess.run(["osascript", "-e", f'display alert "{title}" message "{message}" as critical'], check=False)
        else:
            print(f"[{title}] {message}", file=sys.stderr)
    except Exception as e:
        logger.error("Failed to show error dialog: %s", e)


def global_excepthook(exc_type, exc_value, exc_traceback):
    """Global uncaught exception handler ensuring no crash is silent."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    logger.critical("Unhandled top-level exception:\n%s", tb_str)
    show_error_dialog(
        "Huawei EMS B1 Manager - Startup Error",
        f"A critical error occurred while launching the application:\n\n{exc_value}\n\nLog file location:\n{LOG_FILE}\n\nTechnical details:\n{tb_str[:600]}"
    )


sys.excepthook = global_excepthook
if hasattr(threading, "excepthook"):
    threading.excepthook = lambda args: global_excepthook(args.exc_type, args.exc_value, args.exc_traceback)


# Configure Windows DLL search path for pywebview, pythonnet, and WebView2Loader
if sys.platform == "win32":
    exe_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    internal_dir = Path(getattr(sys, "_MEIPASS", exe_dir))
    search_dirs = [
        str(exe_dir),
        str(internal_dir),
        str(internal_dir / "webview" / "lib"),
        str(internal_dir / "webview" / "lib" / "runtimes" / "win-x64" / "native"),
        str(internal_dir / "runtimes" / "win-x64" / "native"),
    ]
    cur_path = os.environ.get("PATH", "")
    for sd in search_dirs:
        if os.path.exists(sd) and sd not in cur_path:
            os.environ["PATH"] = sd + ";" + os.environ["PATH"]


def is_webview2_available() -> bool:
    """Check if Microsoft Edge WebView2 runtime is installed on Windows."""
    if sys.platform != "win32":
        return True
    try:
        import winreg
        keys = [
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
            r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
        ]
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for k in keys:
                try:
                    with winreg.OpenKey(root, k) as reg_key:
                        val, _ = winreg.QueryValueEx(reg_key, "pv")
                        if val and val != "0.0.0.0":
                            return True
                except Exception:
                    continue
    except Exception as e:
        logger.debug("Error verifying WebView2 registry: %s", e)
    return False


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


server_startup_error: Optional[str] = None
_uvicorn_server = None


def run_uvicorn_server(host: str, port: int, server_ready_event: threading.Event):
    """Run Uvicorn FastAPI server in background thread with crash capture."""
    global server_startup_error, _uvicorn_server
    try:
        import uvicorn
        from app.main import app

        # IMPORTANT: log_config=None prevents Uvicorn from checking sys.stdout.isatty()
        # which crashes PyInstaller windowed executables on Windows with AttributeError.
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_config=None,
            log_level="info",
            access_log=False,
            loop="asyncio"
        )
        server = uvicorn.Server(config)
        _uvicorn_server = server
        server_ready_event.set()
        logger.info("Uvicorn server initialized on %s:%d. Starting serve loop...", host, port)
        server.run()
    except Exception as exc:
        server_startup_error = traceback.format_exc()
        logger.error("Uvicorn server failed: %s", server_startup_error)
        server_ready_event.set()


def wait_for_server(url: str, server_thread: Optional[threading.Thread] = None, timeout: float = 15.0) -> bool:
    """Wait for backend server health check, explicitly bypassing system proxies to prevent localhost timeouts."""
    global server_startup_error
    start_time = time.time()
    proxy_handler = urllib.request.ProxyHandler({})
    opener = urllib.request.build_opener(proxy_handler)

    while time.time() - start_time < timeout:
        if server_startup_error:
            logger.error("Early server failure detected: %s", server_startup_error)
            return False
        if server_thread is not None and not server_thread.is_alive():
            logger.error("Server thread died unexpectedly during startup.")
            return False
        try:
            req = urllib.request.Request(f"{url}/api/health", headers={"User-Agent": "HuaweiBMSDesktop/1.0"})
            with opener.open(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def _run_app():
    parser = argparse.ArgumentParser(description="Huawei EMS B1 Battery Manager Desktop Application")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--headless", "--no-gui", action="store_true", help="Run in headless server mode without desktop window")
    parser.add_argument("--browser", action="store_true", help="Force opening in system browser instead of native desktop window")
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
                logger.info("Huawei EMS B1 Battery Manager is already running on %s", app_url)
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
    if not wait_for_server(app_url, server_thread=server_thread, timeout=15.0):
        error_msg = server_startup_error or "FastAPI server did not respond to health check in time."
        logger.error("Failed to start server within timeout. %s", error_msg)
        show_error_dialog(
            "Huawei EMS B1 Manager - Startup Error",
            f"The application backend failed to start.\n\nError details:\n{error_msg[:600]}\n\nLog file location:\n{LOG_FILE}"
        )
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

    # Browser forced mode
    if args.browser:
        logger.info("Browser mode requested. Opening system browser: %s", app_url)
        webbrowser.open(app_url)
        try:
            while server_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
        return

    # Desktop GUI Window Mode
    gui_started = False
    webview2_ready = is_webview2_available()

    if not webview2_ready and sys.platform == "win32":
        logger.warning("Microsoft Edge WebView2 runtime not found. Opening in system browser for maximum compatibility.")
        webbrowser.open(app_url)
        logger.info("Serving Huawei EMS B1 Battery Manager in default browser: %s", app_url)
        try:
            while server_thread.is_alive():
                time.sleep(1.0)
        except KeyboardInterrupt:
            logger.info("Shutdown requested.")
    else:
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
            gui_launch_start = time.time()
            webview.start(debug=False)
            gui_duration = time.time() - gui_launch_start
            logger.info("Desktop window session ended after %.2f seconds.", gui_duration)
            if gui_duration < 2.0:
                raise RuntimeError(f"Native desktop window closed unexpectedly after {gui_duration:.2f}s")
        except Exception as e:
            logger.warning("Native webview encountered an issue (%s). Falling back to default web browser.", e)
            webbrowser.open(app_url)
            logger.info("Serving Huawei EMS B1 Battery Manager in default browser: %s", app_url)
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


def main():
    try:
        _run_app()
    except Exception as exc:
        err = traceback.format_exc()
        logger.critical("Fatal error during execution: %s", err)
        show_error_dialog(
            "Huawei EMS B1 Manager - Fatal Crash",
            f"Application crashed unexpectedly:\n\n{str(exc)}\n\nFull log saved to:\n{LOG_FILE}"
        )
        sys.exit(1)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
