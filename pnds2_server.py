from flask import Flask, request
import os
import json

app = Flask(__name__)
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
TOKEN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")

os.makedirs(BASE_DIR, exist_ok=True)
os.makedirs(TOKEN_DIR, exist_ok=True)

def get_tokens(filename):
    token_file = os.path.join(TOKEN_DIR, f"{filename}.tokens")
    if os.path.exists(token_file):
        with open(token_file, 'r') as f:
            return json.load(f)
    return None

def save_tokens(filename, tokens):
    token_file = os.path.join(TOKEN_DIR, f"{filename}.tokens")
    with open(token_file, 'w') as f:
        json.dump(tokens, f, indent=2)

def is_privileged(token, tokens):
    """Check if token is owner or admin (both have full rights)."""
    if not token or not tokens:
        return False
    return token == tokens.get('owner') or token == tokens.get('admin')

def check_permission(filename, mode, provided_token=None):
    tokens = get_tokens(filename)
    if tokens is None:
        return True
    # Owner or admin can do anything
    if is_privileged(provided_token, tokens):
        return True
    required = tokens.get(mode)
    if required is None:   # public
        return True
    return provided_token == required

@app.route('/process', methods=['GET', 'POST'])
def process():
    mode = request.values.get('mode')
    filename = request.values.get('file')
    token = request.values.get('token')
    data = request.values.get('data', '')

    if mode != 'l' and not filename:
        return "Error: filename required", 400

    if filename:
        filename = os.path.basename(filename)
        file_path = os.path.join(BASE_DIR, filename)
    else:
        file_path = None

    if mode == 'c':
        if not filename:
            return "Error: filename required", 400
        if get_tokens(filename) is not None:
            return "Error: File already claimed", 400
        if not token:
            return "Error: Owner token required for claiming", 400
        tokens = {
            "owner": token,
            "admin": token,      # default admin = owner
            "r": token,
            "w": token,
            "a": token
        }
        save_tokens(filename, tokens)
        return "File claimed successfully"

    elif mode == 'mt':
        if not filename:
            return "Error: filename required", 400
        tokens = get_tokens(filename)
        if tokens is None:
            return "Error: File not claimed", 400
        # Allow owner or admin
        if not is_privileged(token, tokens):
            return "Error: Invalid admin/owner token", 403
        try:
            new = json.loads(data)
        except:
            return "Error: Invalid token data format", 400
        for key, value in new.items():
            if key == 'owner':
                continue   # owner cannot be changed via modify command
            if key in tokens:
                tokens[key] = value
        save_tokens(filename, tokens)
        return "Tokens updated successfully"

    elif mode == 'w':
        if not filename:
            return "Error: filename required", 400
        if not check_permission(filename, 'w', token):
            return "Error: No write permission", 403
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        return "OK"

    elif mode == 'a':
        if not filename:
            return "Error: filename required", 400
        if not check_permission(filename, 'a', token):
            return "Error: No append permission", 403
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(data)
        return "OK"

    elif mode == 'r':
        if not filename:
            return "Error: filename required", 400
        if not check_permission(filename, 'r', token):
            return "Error: No read permission", 403
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"NoFileExists:{filename}", 404

    elif mode == 'l':
        if not token:
            return "Error: Token required", 400
        owned = []
        for tf in os.listdir(TOKEN_DIR):
            if tf.endswith('.tokens'):
                fname = tf[:-7]
                t = get_tokens(fname)
                if t and t.get('owner') == token:
                    owned.append(fname)
        return json.dumps(owned)

    elif mode == 'lt':
        if not filename:
            return "Error: filename required", 400
        tokens = get_tokens(filename)
        if tokens is None:
            return "Error: File not claimed", 400
        if not token:
            return "Error: Token required", 400
        is_owner = (token == tokens.get('owner'))
        is_admin = (token == tokens.get('admin'))
        if not is_owner and not is_admin:
            return "Error: Invalid admin/owner token", 403

        result = {"filename": filename}
        if is_owner:
            # Owner sees everything
            result["owner"] = tokens.get('owner')
            result["admin"] = tokens.get('admin')
            result["r"] = tokens.get('r')
            result["w"] = tokens.get('w')
            result["a"] = tokens.get('a')
        else:  # admin (not owner)
            result["admin"] = tokens.get('admin')
            result["r"] = tokens.get('r')
            result["w"] = tokens.get('w')
            result["a"] = tokens.get('a')
        return json.dumps(result, indent=2)

    else:
        return "Invalid mode", 400

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
