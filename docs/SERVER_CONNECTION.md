# Server Connection Guide

This document provides a complete technical description of the current, working SSH configuration used to connect the VS Code dev container to the `trad` server.

## Connection Details

- **Server IP Address:** `138.68.245.159`
- **SSH User:** `root`
- **Authentication Method:** SSH Key Forwarding via `ssh-agent`

## Technical Configuration

The connection relies on forwarding the SSH authentication from your local machine (the one running VS Code) to the dev container, and then from the container to the server. This avoids the need to store private keys directly on the server or within the dev container.

### 1. Local Machine Setup (macOS, Linux, or WSL)

The `ssh-agent` must be running on your local machine, and your private SSH key (e.g., `~/.ssh/id_rsa`) must be added to it.

**To check if the agent is running:**
```bash
eval "$(ssh-agent -s)"
```

**To add your key to the agent:**
```bash
ssh-add ~/.ssh/id_rsa
```
*(Replace `~/.ssh/id_rsa` with the path to your specific private key if it's different.)*

### 2. VS Code Dev Container Configuration

The dev container is automatically configured by VS Code to forward the SSH agent from your local machine into the container. This is a built-in feature when using the "Remote - Containers" extension and does not require manual setup within the container itself.

### 3. Connection Command

To connect to the server from the dev container's terminal, the following command is used. The `-A` flag is critical as it enables the forwarding of the authentication agent connection.

```bash
ssh -A root@138.68.245.159
```

### 4. How It Works (The Chain of Connection)

1.  **Local Machine:** `ssh-agent` holds your private key.
2.  **VS Code:** Connects to the dev container and forwards the `ssh-agent` socket.
3.  **Dev Container:** The `ssh` client inside the container uses the forwarded agent socket to authenticate.
4.  **Server:** The server at `138.68.245.159` receives the authentication request, validates it against the public key stored in `/root/.ssh/authorized_keys`, and grants access.

## Troubleshooting

If the connection fails with a `Permission denied (publickey)` error, follow these steps:

1.  **Verify `ssh-agent` on Local Machine:** Run `ssh-add -l` on your local machine's terminal (not the dev container's). If you don't see your key listed, run `ssh-add` again.
2.  **Check VS Code Forwarding:** Ensure that you are properly connected to the dev container via the "Remote - Containers" extension.
3.  **Test Direct Connection:** Try connecting directly from your local machine's terminal (`ssh root@138.68.245.159`). If this fails, the issue is with your key pair or the server's `authorized_keys` file. If it succeeds, the issue is with the agent forwarding to the container.
4.  **Firewall:** Ensure that the server's firewall (`ufw`) allows SSH connections on port 22.
