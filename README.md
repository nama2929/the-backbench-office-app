# THE BACKBENCH — Office Edition

A polished, small-group **real-time multiplayer Streamlit game** for 6–7 office colleagues. Good for an MP office with students and early-career staff: funny mock bills, collaborative voting, a moderated noticeboard, and synchronized celebrations. **Not an official parliamentary platform.** No Wi-Fi monitoring, tracking, political campaigning, or relationship/gossip games.

## What everyone can do

- **The House:** Propose a harmless office bill, vote Aye / No / Abstain, view live counts. The host can close voting and the app announces the result.
- **Noticeboard:** Send appreciations, constructive ideas, or a light office moment. The host approves before anyone sees it; one reaction per person per message.
- **Live Moments:** The host triggers a celebratory animation/announcement that appears on all open app tabs within ~3 seconds and clears automatically.
- **Team Lounge:** See who is active **in the app** (not physically present).
- **Host Console:** Message moderation, live broadcasts, and voting controls.

No fake stats: everything except example suggestions originates from real teammates using the app.

## One laptop + 6–7 players on the same Wi-Fi (Windows)

1. Download the ZIP; extract it to your computer.
2. Install Python 3.10+ from [python.org](https://www.python.org/downloads/). On Windows, allow `py` in your terminal.
3. Double-click **`RUN_WINDOWS.bat`**. It creates a Python virtual environment, installs Streamlit, and starts the server. Or in VS Code PowerShell:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
   ```

4. On the host computer, open `http://localhost:8501`.
5. **The first visitor** creates a **room access code** (6+ characters) and a **different host PIN** (6+ characters). Keep the host PIN private; share only the room code.
6. Join as a new player using a nickname and a personal PIN (4+ characters). On returning, use the same nickname and personal PIN.
7. Find the hosting laptop's LAN IPv4 address:

   ```powershell
   ipconfig
   ```

   Under your connected Wi-Fi adapter, note the **IPv4 Address** (e.g., `192.168.1.8`). Everyone on the **same trusted Wi-Fi** opens `http://192.168.1.8:8501`, substituting your actual IP.
8. If other laptops cannot open it, allow Python/Streamlit through Windows Defender Firewall for **Private networks**. Do not open a public firewall rule. Guest Wi-Fi/client isolation may prevent laptop-to-laptop connections.
9. Keep the **host laptop running and awake**, with its terminal still open. Other team members can open/close the site whenever they wish.

On Mac/Linux, run `./run_mac_linux.sh`.

## Quick group demo (3 minutes)

1. Two people join from separate laptops/phones.
2. One creates **The Mandatory 4 PM Chai Resolution**.
3. Each votes from their own laptop and watches totals update every ~3 seconds.
4. Someone writes an **Appreciation**. Host reviews and approves it.
5. Host broadcasts an **Applause** moment. Everyone sees it without refreshing.

## How the multiplayer works

A single Streamlit server and local SQLite database run on the host laptop. Each browser is its own Streamlit session; `st.fragment(run_every='3s')` polls shared SQLite for updated votes, messages, and announcements. SQLite is configured in WAL mode; updates have constraints/transactions to protect simultaneous votes. The app uses room access codes and salted PBKDF2 hashes for personal PINs.

**Important:** This is a trusted-LAN social app, not an enterprise-grade authentication or encrypted internet deployment. Do NOT expose `--server.address 0.0.0.0` directly to the public internet with port forwarding. A publicly hosted multi-user edition should add HTTPS, trusted authentication, a managed database such as Postgres, and appropriate admin permissions. GitHub hosts the code, not a running Streamlit server.

## Privacy and appropriateness

- No relationship questions, invasive gossip, names in mock allegations, or embarrassing challenges.
- Do not share confidential constituency, employee, or parliamentary information.
- **Noticeboard posts are not truly anonymous:** the host can see the author during moderation, and the database stores them. The public board displays a generic team label after approval.
- No invisible tracking: only users who join the site appear in the Team Lounge.
- Data is stored under `data/backbenchers.sqlite3` on the host. This file is ignored by Git, as are temporary SQLite files and credentials. Back it up locally if necessary; delete it to erase the entire room (while app is stopped).
- Personal PINs should not be reused from important services.

## File structure

```
Backbenchers_Office_Edition/
├── app.py                  # Streamlit UI and live polling
├── storage.py              # SQLite storage, logins, votes, moderation
├── requirements.txt        # Streamlit
├── RUN_WINDOWS.bat         # One-click Windows launcher
├── run_mac_linux.sh        # Mac/Linux launcher
├── .streamlit/config.toml  # Theme settings
├── .gitignore              # Excludes data and secrets
└── tests/test_storage.py   # Local unit tests
```

## Run tests

From the project root:

```powershell
py -m unittest discover -s tests -v
```

## GitHub

Create a **private repository** in GitHub and upload this project. The `.gitignore` keeps the SQLite data and secrets out of source control, but always inspect `git status` before committing. For coworkers, share the **local-network URL** while the host laptop is on; a GitHub repository URL is *not* the playable multiplayer website.

## Troubleshooting

- **Other people can't reach the site:** Check the host IPv4, that the Streamlit console is still running, firewall Private-network permission, same SSID, and router client isolation.
- **Old vote counts / missed events:** Leave the site open and ensure the server is running. Screens automatically refresh every 3 seconds; if the device sleeps/disconnects, updates resume after reconnect.
- **Nickname already exists:** Use the Returning Player tab with your personal PIN.
- **Forgot host PIN:** Back up then reset the local SQLite room file. This erases content too; there is no unsafe backdoor password-reset route.
- **App not visible after GitHub upload:** GitHub is code hosting, not an always-on app host. Local LAN works without paying for cloud hosting.
