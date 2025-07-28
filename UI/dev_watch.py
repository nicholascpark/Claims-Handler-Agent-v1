import sys
import time
import subprocess
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class AppRestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.restart_app()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Only restart on Python file changes
        if event.src_path.endswith('.py'):
            print(f"📝 File changed: {event.src_path}")
            print("🔄 Restarting IntactBot...")
            self.restart_app()
    
    def restart_app(self):
        # Kill existing process
        if self.process:
            self.process.terminate()
            self.process.wait()
        
        # Start new process
        self.process = subprocess.Popen([sys.executable, "app.py"])
        print("✅ IntactBot restarted!")
    
    def cleanup(self):
        if self.process:
            self.process.terminate()

def main():
    print("🚀 Starting IntactBot Development Watcher...")
    print("📁 Watching UI/ and src/ directories for changes...")
    print("💡 Press Ctrl+C to stop\n")
    
    # Paths to watch
    paths_to_watch = [".", "../src"]
    
    event_handler = AppRestartHandler()
    observer = Observer()
    
    for path in paths_to_watch:
        if os.path.exists(path):
            observer.schedule(event_handler, path, recursive=True)
            print(f"👀 Watching: {path}")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Stopping watcher...")
        event_handler.cleanup()
        observer.stop()
    
    observer.join()
    print("✅ Watcher stopped!")

if __name__ == "__main__":
    main() 