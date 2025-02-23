#!/usr/bin/env python3
import json
import time
import signal
import sys
import os
import atexit
from datetime import datetime
from colorama import Fore, Style, init
from websocket import WebSocketApp
from itertools import cycle

init(autoreset=True)

class TestClient:
    def __init__(self):
        config = self.load_config()
        self.ws_url = config["ws_url"]
        self.repo_url = config["repo_url"]
        self.user_id = config["user_id"]
        self.chat_id = config["chat_id"]
        self.project_type = config["project_type"]
        self.commits = config["commits"]
        self.test_command = config.get("test_command", "pytest tests/")
        self.results = []
        self.current_commit = None
        self.start_time = None
        self.ws = None
        self.spinner = cycle(["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"])
        atexit.register(self.print_summary)  # Ensure summary is printed on exit

    def print_header(self):
        print(f"\n{Fore.CYAN}🚀 WebSocket Test Client")
        print(f"{Fore.YELLOW}► Repo: {Style.RESET_ALL}{self.repo_url}")
        print(f"{Fore.YELLOW}► Commits: {Style.RESET_ALL}{len(self.commits)}")
        print(f"{Fore.YELLOW}► Server: {Style.RESET_ALL}{self.ws_url}")
        print(f"\n{Fore.MAGENTA}⚡ Press Ctrl+C to exit\n")

    def show_spinner(self):
        return f"{Fore.CYAN}{next(self.spinner)}"

    def send_next(self):
        if not self.commits:
            print(f"{Fore.GREEN}🎉 All commits processed!")
            self.shutdown()
            return

        self.current_commit = self.commits.pop(0)
        self.start_time = time.time()
        msg = {
            "userId": self.user_id,
            "chatId": self.chat_id,
            "repoURL": self.repo_url,
            "commitHash": self.current_commit,
            "projectType": self.project_type,
            "testCommand": self.test_command or None
        }
        self.ws.send(json.dumps(msg))
        print(f"{Fore.WHITE}📤 Sent: {Fore.YELLOW}{self.current_commit[:7]}")

    def on_open(self, ws):
        print(f"{Fore.GREEN}✅ Connected to server")
        self.send_next()

    def on_message(self, ws, message):
        response_time = time.time() - self.start_time
        try:
            response = json.loads(message)
            status = response.get("type", "unknown")
            self.results.append({
                "commit": self.current_commit,
                "status": status,
                "time": response_time,
                "response": response,
            })
            print(f"\n{Fore.WHITE}─── Response for {Fore.YELLOW}{self.current_commit[:7]} {Fore.WHITE}({response_time:.2f}s) {'─'*40}")
            self.print_response(response)
            self.send_next()
        except json.JSONDecodeError:
            print(f"{Fore.RED}❌ Invalid JSON response: {message}")

    def print_response(self, response):
        status_color = Fore.GREEN if response.get("type") == "test_results" else Fore.RED
        print(f"{status_color}Status: {response.get('type', 'unknown')}")
        print(f"{Fore.CYAN}┌{'─'*60}┐")
        formatted_json = json.dumps(response, indent=2)
        for line in formatted_json.split("\n"):
            print(f"{Fore.CYAN}│ {Fore.WHITE}{line}")
        print(f"{Fore.CYAN}└{'─'*60}┘")

    def on_error(self, ws, error):
        print(f"\n{Fore.RED}🚨 WebSocket Error: {repr(error)}")

    def on_close(self, ws, status, msg):
        print(f"\n{Fore.CYAN}🔌 Connection closed")

    def print_summary(self):
        if not self.results:
            return
        print(f"\n{Fore.CYAN}📊 Test Summary Report")
        print(f"{Fore.MAGENTA}╭{'─'*78}╮")
        total = len(self.results)
        success = sum(1 for r in self.results if r["status"] == "test_results")
        failures = total - success
        total_time = sum(r["time"] for r in self.results)
        avg_time = total_time / total if total > 0 else 0
        print(f"{Fore.MAGENTA}│ {Fore.WHITE}🚀 Total Tests: {Fore.CYAN}{total:<4} {Fore.GREEN}✅ Passed: {success:<4} {Fore.RED}❌ Failed: {failures:<4} {Fore.YELLOW}⏳ Avg Time: {avg_time:.2f}s")
        print(f"{Fore.MAGENTA}├{'─'*78}┤")
        for idx, result in enumerate(self.results, 1):
            color = Fore.GREEN if result["status"] == "test_results" else Fore.RED
            symbol = "✅" if result["status"] == "test_results" else "❌"
            line = f"{Fore.MAGENTA}│ {Fore.WHITE}{idx:03d} {color}{symbol} {Fore.CYAN}{result['commit'][:7]} {Fore.WHITE}➔ {color}{result['status'].upper():<15} {Fore.YELLOW}{result['time']:>5.2f}s"
            print(line)
        print(f"{Fore.MAGENTA}╰{'─'*78}╯")

    def run(self):
        self.print_header()
        self.ws = WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        signal.signal(signal.SIGINT, lambda s, f: self.shutdown())
        signal.signal(signal.SIGTERM, lambda s, f: self.shutdown())
        self.ws.run_forever()

    def shutdown(self):
        print(f"\n{Fore.RED}🛑 Graceful shutdown initiated...")
        if self.ws:
            self.ws.close()
        sys.exit(0)

    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), "..", "config.json")
        try:
            with open(config_path) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            print(f"{Fore.RED}❌ Error loading config file: {config_path}")
            sys.exit(1)

if __name__ == "__main__":
    client = TestClient()
    client.run()