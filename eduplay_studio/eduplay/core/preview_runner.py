import sys
import os

def build_preview_process_command(*, executable: str, uri: str, title: str, frozen: bool) -> tuple[str, list[str]]:
    program = str(executable or "")
    safe_uri = str(uri or "")
    safe_title = str(title or "EduPlay Preview")
    if frozen:
        return program, ["--preview-runner", safe_uri, safe_title]
    return program, ["-u", "-m", "eduplay.core.preview_runner", safe_uri, safe_title]


def _run_qt_preview(uri: str, title: str) -> bool:
    try:
        from PySide6.QtCore import QTimer, QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow
        from PySide6.QtWebEngineWidgets import QWebEngineSettings, QWebEngineView
    except Exception:
        return False

    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle(str(title or "EduPlay Preview"))
    window.resize(1280, 840)
    window.showMaximized()

    web_view = QWebEngineView()
    try:
        settings = web_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        settings.setAttribute(QWebEngineSettings.Accelerated2DCanvasEnabled, True)
    except Exception:
        pass
    try:
        web_view.page().setAudioMuted(False)
    except Exception:
        pass

    ready_state = {"printed": False}

    def _print_ready():
        if ready_state["printed"]:
            return
        ready_state["printed"] = True
        try:
            print("EDUPLAY_PREVIEW_READY", flush=True)
        except Exception:
            pass

    try:
        web_view.loadStarted.connect(lambda: QTimer.singleShot(0, _print_ready))
    except Exception:
        pass
    QTimer.singleShot(0, _print_ready)

    window.setCentralWidget(web_view)
    try:
        web_view.setUrl(QUrl(str(uri or "")))
    except Exception:
        return False
    window.show()

    if owns_app:
        app.exec()
        return True

    try:
        app.exec()
    except Exception:
        return False
    return True


def main():
    argv = list(sys.argv[1:])
    if argv and argv[0] == "--preview-runner":
        argv = argv[1:]
    if len(argv) < 1:
        print("Usage: python -m eduplay.core.preview_runner <file_or_url> [title]")
        sys.exit(1)
    uri = argv[0]
    title = argv[1] if len(argv) > 1 else "EduPlay Preview"
    try:
        os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu --disable-software-rasterizer")
    except Exception:
        pass
    try:
        if _run_qt_preview(uri, title):
            return
    except Exception as e:
        print("Qt preview fallback failed:", e)
    try:
        import webview
    except Exception as e:
        print("pywebview is not installed:", e)
        sys.exit(2)
    try:
        # Prefer native Edge backend on Windows if available
        try:
            def _ready():
                try:
                    print("EDUPLAY_PREVIEW_READY", flush=True)
                except Exception:
                    pass
            try:
                webview.create_window(title, uri, easy_drag=False, maximized=True)
            except TypeError:
                try:
                    webview.create_window(title, uri, easy_drag=False)
                except TypeError:
                    webview.create_window(title, uri)
            webview.start(_ready, gui='edgechromium', debug=False)
            return
        except Exception:
            pass
        # Fallback to Qt backend if Edge is not available
        try:
            def _ready2():
                try:
                    print("EDUPLAY_PREVIEW_READY", flush=True)
                except Exception:
                    pass
            try:
                webview.create_window(title, uri, easy_drag=False, maximized=True)
            except TypeError:
                try:
                    webview.create_window(title, uri, easy_drag=False)
                except TypeError:
                    webview.create_window(title, uri)
            webview.start(_ready2, gui='qt', debug=False)
            return
        except Exception:
            pass
        # Last resort: backend auto-detection
        def _ready3():
            try:
                print("EDUPLAY_PREVIEW_READY", flush=True)
            except Exception:
                pass
        try:
            webview.create_window(title, uri, easy_drag=False, maximized=True)
        except TypeError:
            try:
                webview.create_window(title, uri, easy_drag=False)
            except TypeError:
                webview.create_window(title, uri)
        webview.start(_ready3, debug=False)
    except Exception as e:
        print("Failed to start webview:", e)
        sys.exit(3)

if __name__ == "__main__":
    main()

