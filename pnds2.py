import requests
import os
import sys
import json
import cmd
import shlex
from datetime import datetime

class PublicNetworkingClient(cmd.Cmd):
    intro = """
    ╔══════════════════════════════════════════════════════════╗
    ║     PNDS v2 - Public Networking Data System             ║
    ║     Interactive File Management with Token Security     ║
    ╚══════════════════════════════════════════════════════════╝
    
    Type 'help' or '?' to list commands.
    Type 'exit' or 'quit' to leave.
    """
    prompt = 'PNDS> '

    def __init__(self):
        super().__init__()
        self.server_url = "https://hellker120.pythonanywhere.com/process"  # adjust if needed
        self.session = requests.Session()
        self.current_token = None

    def _send_request(self, filename, mode, token=None, data=None):
        payload = {'file': filename or '', 'mode': mode}
        if token:
            payload['token'] = token
        elif self.current_token and mode not in ['c']:
            payload['token'] = self.current_token
        if data is not None:
            payload['data'] = json.dumps(data) if isinstance(data, dict) else data
        try:
            if mode in ['r', 'l', 'lt']:
                resp = self.session.get(self.server_url, params=payload)
            else:
                resp = self.session.post(self.server_url, data=payload)
            return resp.text
        except Exception as e:
            return f"Error: {str(e)}"

    def _safe_filename(self, f):
        return os.path.basename(f)

    def _parse_json(self, s):
        try:
            return json.loads(s)
        except:
            return None

    def do_create(self, arg):
        """Create/overwrite a file. Usage: create <filename> <content> [token]"""
        parts = shlex.split(arg)
        if len(parts) < 2:
            print("Error: Need filename and content")
            return
        fname = self._safe_filename(parts[0])
        content = parts[1]
        token = parts[2] if len(parts) > 2 else None
        result = self._send_request(fname, 'w', token, content)
        print("✓" if result == "OK" else f"✗ {result}")

    def do_read(self, arg):
        """Read a file. Usage: read <filename> [token]"""
        parts = shlex.split(arg)
        if len(parts) < 1:
            print("Error: Need filename")
            return
        fname = self._safe_filename(parts[0])
        token = parts[1] if len(parts) > 1 else None
        result = self._send_request(fname, 'r', token)
        if result.startswith("NoFileExists"):
            print(f"✗ File '{fname}' does not exist")
        elif result.startswith("Error:"):
            print(f"✗ {result}")
        else:
            print(f"📄 Contents of '{fname}':")
            print("-" * 40)
            print(result)
            print("-" * 40)

    def do_append(self, arg):
        """Append to a file. Usage: append <filename> <content> [token]"""
        parts = shlex.split(arg)
        if len(parts) < 2:
            print("Error: Need filename and content")
            return
        fname = self._safe_filename(parts[0])
        content = parts[1]
        token = parts[2] if len(parts) > 2 else None
        result = self._send_request(fname, 'a', token, content)
        print("✓" if result == "OK" else f"✗ {result}")

    def do_claim(self, arg):
        """Claim a public file. Usage: claim <filename> <owner_token>"""
        parts = shlex.split(arg)
        if len(parts) < 2:
            print("Error: Need filename and owner token")
            return
        fname = self._safe_filename(parts[0])
        owner = parts[1]
        print(self._send_request(fname, 'c', owner))

    def do_modify(self, arg):
        """
        Modify tokens. Usage: modify <filename> <admin_token> <json_updates>
        Example: modify notes.txt MyAdminToken {"r": null, "w": "new123"}
        """
        parts = arg.split(maxsplit=2)   # keep JSON intact
        if len(parts) < 3:
            print("Error: Need filename, admin token, and JSON updates")
            print("Example: modify notes.txt MyAdminToken {'r': null, 'w': 'new123'}")
            return
        fname = self._safe_filename(parts[0])
        admin = parts[1]
        updates = parts[2]
        if not self._parse_json(updates):
            print("✗ Invalid JSON format (use double quotes)")
            return
        print(self._send_request(fname, 'mt', admin, updates))

    def do_list(self, arg):
        """List owned files. Usage: list [owner_token] (uses session token if omitted)"""
        token = arg.strip() if arg.strip() else self.current_token
        if not token:
            print("Error: No owner token provided and no session token set.")
            return
        result = self._send_request('', 'l', token)
        try:
            files = json.loads(result)
            if isinstance(files, list):
                if files:
                    print(f"📁 Your files ({len(files)}):")
                    for f in files:
                        print(f"  • {f}")
                else:
                    print("No files found for this token")
            else:
                print(result)
        except json.JSONDecodeError:
            print(result)

    def do_tokens(self, arg):
        """Show token info. Usage: tokens <filename> <admin_token>"""
        parts = shlex.split(arg)
        if len(parts) < 2:
            print("Error: Need filename and admin/owner token")
            return
        fname = self._safe_filename(parts[0])
        token = parts[1]
        result = self._send_request(fname, 'lt', token)
        try:
            info = json.loads(result)
            print(f"🔐 Token info for '{fname}':")
            print("-" * 30)
            for k, v in info.items():
                if k != 'filename':
                    print(f"  {k}: {v}")
        except:
            print(result)

    def do_download(self, arg):
        """Download a file. Usage: download <filename> [token]"""
        parts = shlex.split(arg)
        if len(parts) < 1:
            print("Error: Need filename")
            return
        fname = self._safe_filename(parts[0])
        token = parts[1] if len(parts) > 1 else None
        result = self._send_request(fname, 'r', token)
        if result.startswith("NoFileExists"):
            print(f"✗ File '{fname}' does not exist")
        elif result.startswith("Error:"):
            print(f"✗ {result}")
        else:
            local = f"downloaded_{fname}"
            with open(local, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"✓ Downloaded '{fname}' to '{local}'")

    def do_upload(self, arg):
        """Upload a local file. Usage: upload <local_file> [remote_filename] [token]"""
        parts = shlex.split(arg)
        if len(parts) < 1:
            print("Error: Need local filename")
            return
        local = parts[0]
        if not os.path.exists(local):
            print(f"✗ Local file '{local}' does not exist")
            return
        remote = parts[1] if len(parts) > 1 else local
        token = parts[2] if len(parts) > 2 else None
        try:
            with open(local, 'r', encoding='utf-8') as f:
                content = f.read()
            result = self._send_request(remote, 'w', token, content)
            print("✓" if result == "OK" else f"✗ {result}")
        except Exception as e:
            print(f"✗ Error reading file: {e}")

    def do_settoken(self, arg):
        """Set default token. Usage: settoken <token>"""
        if not arg:
            print("Current token: " + (self.current_token or "None"))
        else:
            self.current_token = arg.strip()
            print(f"✓ Session token set to: {self.current_token}")

    def do_info(self, arg):
        print(f"🌐 Server: {self.server_url}")
        print(f"🔑 Session token: {self.current_token or 'Not set'}")
        print(f"⏰ Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def do_clear(self, arg):
        os.system('cls' if os.name == 'nt' else 'clear')

    def do_exit(self, arg):
        print("Goodbye! 👋")
        return True
    do_quit = do_exit

    def do_EOF(self, arg):
        print()
        return self.do_exit(arg)

    def complete_download(self, text, line, begidx, endidx):
        return [f for f in os.listdir('.') if f.startswith(text)]
    def complete_upload(self, text, line, begidx, endidx):
        return [f for f in os.listdir('.') if f.startswith(text)]

if __name__ == "__main__":
    try:
        PublicNetworkingClient().cmdloop()
    except KeyboardInterrupt:
        print("\nGoodbye! 👋")
        sys.exit(0)
