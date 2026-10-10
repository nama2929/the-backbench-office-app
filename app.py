"""The Backbench — friendly, real-time multiplayer office game for 6–7 people.

Start on one computer; others visit http://YOUR-LAN-IP:8501.
The database is on the host computer, not a cloud service.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import escape
import streamlit as st
import storage as db

IST = timezone(timedelta(hours=5, minutes=30))
st.set_page_config(
    page_title='The Backbench | Office Edition',
    page_icon='🏛️',
    layout='wide',
    initial_sidebar_state='expanded',
)

def e(value: str) -> str:
    return escape(str(value), quote=True)


def clock(t: int) -> str:
    return datetime.fromtimestamp(t, IST).strftime('%-I:%M %p') if __import__('os').name != 'nt' else datetime.fromtimestamp(t, IST).strftime('%I:%M %p').lstrip('0')


def day_time(t: int) -> str:
    return datetime.fromtimestamp(t, IST).strftime('%d %b · %I:%M %p')


def inject_style():
    st.markdown('''<style>
      @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
      :root {color-scheme: dark;}
      .stApp {background:radial-gradient(circle at 90% 0%,rgba(42,77,100,.34) 0%,transparent 34%),#0b1020;}
      [data-testid="stSidebar"] {background:#0D1627;border-right:1px solid rgba(213,235,255,.08);}
      .block-container {padding-top:2rem;padding-bottom:4rem;max-width:1180px;}
      h1,h2,h3 {font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.035em;}
      div,p,span,label,button,textarea,input {font-family:'DM Sans',sans-serif;}
      [data-testid="stMetric"] {background:#172138;border:1px solid rgba(166,194,222,.14);padding:18px 16px;border-radius:16px;}
      [data-testid="stMetricLabel"] {font-size:13px!important;}
      [data-testid="stMetricValue"] {font-family:'Space Grotesk',sans-serif;font-size:30px!important;color:#f5f8fe;}
      div.stButton > button[kind="primary"], button[kind="primary"]{background:#38dba9;color:#071625;border:0;font-weight:700;}
      div.stButton > button:hover{border-color:#38dba9;color:#72f1ce;}
      [data-testid="stVerticalBlockBorderWrapper"] {border-color:#283752!important;border-radius:15px!important;background:rgba(22,33,53,.57);}
      .eyebrow{font-size:11px;font-weight:700;letter-spacing:.16em;color:#49e1b2;margin-bottom:9px;}
      .hero{background:linear-gradient(125deg,#152941,#16223b 62%,#123b3b);border:1px solid #304763;padding:28px;border-radius:22px;margin:0 0 19px;box-shadow:0 18px 48px #00000022;}
      .hero h1{font-size:clamp(28px,4vw,44px);margin:3px 0 10px;color:#f8fbff;line-height:1.05;}
      .hero p{max-width:650px;color:#b6c7dc;font-size:15px;margin:0;}
      .pill{display:inline-block;border:1px solid #2c6c62;background:#14342f;border-radius:50px;color:#a2ffe2;padding:5px 11px;font-size:11px;font-weight:700;}
      .soft{color:#9db0c9;font-size:13px;}
      .moment{background:linear-gradient(95deg,#195b53,#174d69 58%,#4a346d);border:1px solid #55bdaa;padding:22px 24px;border-radius:19px;margin:6px 0 20px;box-shadow:0 12px 55px #28f0c514;}
      .moment .kicker{color:#b4fce9;font-size:11px;font-weight:700;letter-spacing:.14em;}
      .moment h2{color:white;margin:6px 0;font-size:26px;}
      .moment p{color:#d7edee;font-size:14px;margin-bottom:0;}
      .bar-track{height:8px;background:#293750;border-radius:20px;overflow:hidden;margin:8px 0 4px;}
      .bar-fill{height:100%;background:linear-gradient(90deg,#37d6ab,#68e5ca);border-radius:20px;}
      .hint{font-size:12px;color:#9fb2ce;line-height:1.6;}
      .brand{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:21px;color:#f8fbff;margin-bottom:2px;}
      .brand span{color:#49e1b2;}
      .member-line{background:#15243a;border:1px solid #2b3b55;border-radius:12px;padding:10px 12px;margin:8px 0;font-size:13px;color:#dce8f8;}
      .dot-online{color:#44efb9;font-weight:700;}.dot-offline{color:#6f859b;font-weight:700;}
      div[data-testid="stAlert"]{border-radius:12px;}
      @media (max-width:650px){.hero{padding:20px}.hero h1{font-size:29px;}.block-container{padding-top:1rem}}
    </style>''', unsafe_allow_html=True)


def hero(label: str, title: str, subtitle: str):
    st.markdown(f'''<div class="hero"><div class="eyebrow">{e(label.upper())}</div>
    <h1>{e(title)}</h1><p>{e(subtitle)}</p></div>''', unsafe_allow_html=True)


def small_bar(label: str, count: int, total: int):
    width = 0 if total == 0 else 100 * count / total
    st.markdown(f'''<div style="display:flex;justify-content:space-between;font-size:13px;color:#ccdaeb;margin-top:8px">
        <span>{e(label)}</span><b>{count}</b></div>
        <div class="bar-track"><div class="bar-fill" style="width:{width:.2f}%"></div></div>''', unsafe_allow_html=True)


def setup_room():
    hero('First time only', 'Set up your private room', 'The first person sets the office access code and a separate host PIN. This runs locally on your computer.')
    left, right = st.columns([1.2, 1])
    with left:
        with st.form('setup'):
            name = st.text_input('Team room name', value='The Backbench · Office Edition', max_chars=65)
            code = st.text_input('Private room access code (6+ characters)', type='password', help='Share this only with coworkers who should join.')
            pin = st.text_input('Host PIN (6+ characters; different from room code)', type='password')
            created = st.form_submit_button('Create room', type='primary', use_container_width=True)
        if created:
            if code == pin:
                st.error('Use a different code for host controls.')
            else:
                try:
                    if db.create_room(name, code, pin):
                        st.success('Room created! Use the same access code to join below.')
                        st.rerun()
                    else:
                        st.warning('This room has already been set up.')
                except ValueError as exc:
                    st.error(str(exc))
    with right:
        st.info('Your room and messages remain on this laptop. No external database or paid service is required.')
        st.markdown('**Ground rules**  \nKind humour. No personal gossip. No political campaigning. No confidential work information. No embarrassing or targeted messages.')


def join_room():
    r = db.room()
    hero('Private team space', 'Welcome to The Backbench.', f"{r['name']} · Real-time office games, live votes, and team moments.")
    left, right = st.columns([1.25, .85])
    with left:
        new_tab, return_tab = st.tabs(['✨ New player', '↩️ Returning player'])
        with new_tab:
            with st.form('join_new'):
                code = st.text_input('Room access code', type='password', key='new_room_code')
                nick = st.text_input('Choose a display nickname', max_chars=24)
                pin = st.text_input('Choose a personal PIN (4+ characters)', type='password', help='Use it to return with the same nickname after refreshing.')
                join = st.form_submit_button('Join the room', type='primary', use_container_width=True)
            if join:
                if not db.validate_room_code(code):
                    st.error('Incorrect room access code.')
                else:
                    try:
                        st.session_state.user = db.register(nick, pin)
                        st.session_state.host = False
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        with return_tab:
            with st.form('join_return'):
                code_r = st.text_input('Room access code', type='password', key='return_room_code')
                nick_r = st.text_input('Your existing nickname', key='return_nick')
                pin_r = st.text_input('Your personal PIN', type='password', key='return_pin')
                go = st.form_submit_button('Rejoin', type='primary', use_container_width=True)
            if go:
                if not db.validate_room_code(code_r):
                    st.error('Incorrect room access code.')
                else:
                    user = db.login(nick_r, pin_r)
                    if user:
                        st.session_state.user = user
                        st.session_state.host = False
                        st.rerun()
                    else:
                        st.error('Nickname or personal PIN does not match.')
    with right:
        with st.container(border=True):
            st.subheader('What happens inside?')
            st.markdown('🏛️ **The House** — propose and vote on harmless office bills  \n\n💬 **The Noticeboard** — appreciations, ideas, and light moments  \n\n✨ **Live Moments** — synchronized celebration or surprise prompts  \n\n🟢 **Team Lounge** — see who has joined the room')
            st.caption('Messages are moderated before appearing. This is a friendly, not anonymous, workplace space.')


def moment_banner():
    m = db.current_moment()
    if not m:
        return
    key = f"seen_{m['id']}"
    if not st.session_state.get(key):
        st.session_state[key] = True
        if m['kind'] == 'Applause' and st.session_state.get('effects', True):
            st.balloons()
    seconds = max(0, m['expires_at'] - db.now())
    st.markdown(f'''<div class="moment" role="status"><div class="kicker">✦ LIVE TEAM MOMENT · {e(m['kind'].upper())} · {seconds}s</div>
        <h2>{e(m['title'])}</h2><p>{e(m['detail'])}</p></div>''', unsafe_allow_html=True)


def home(user):
    hero('Room is live', f"Hey, {user['nickname']} 👋", 'A private corner for ideas, inside jokes, and the kind of debate that never makes it into the minutes.')
    s = db.stats()
    cells = st.columns(4)
    for c, label, value in zip(cells, ('Online now','Team members','Bills proposed','Bills passed'), (s['online'],s['people'],s['proposals'],s['passed'])):
        c.metric(label, value)
    st.write('')
    left, right = st.columns([1.2,1], gap='large')
    with left:
        st.subheader('🏛️ The House is in session')
        st.write('Propose tiny office resolutions. Vote on everybody’s laptop. Let the numbers decide.')
        for example in ('A 4 PM chai break should be part of the office constitution.',
                        'The person who picks lunch should also pick the restaurant.',
                        'Meeting agendas should fit on one page.'):
            st.markdown(f'<div class="member-line">{e(example)}</div>', unsafe_allow_html=True)
        st.caption('For fun only. Votes do not set real workplace policy.')
    with right:
        st.subheader('🟢 Who’s here?')
        team = db.members()
        if not team:
            st.caption('No players yet.')
        for person in team:
            active = db.now()-person['last_seen'] < 25
            status = '<span class="dot-online">● ONLINE</span>' if active else '<span class="dot-offline">● AWAY</span>'
            st.markdown(f'''<div class="member-line"><b>{e(person['nickname'])}</b><span style="float:right">{status}</span></div>''', unsafe_allow_html=True)
        st.caption('Online means their Backbench browser is actively refreshing; not their physical office presence.')


def house(user, host):
    hero('01 / The House', 'Bills. Banter. Democracy.', 'Make a lighthearted proposal, vote once per member (you may change while open), and see live results.')
    with st.expander('➕ Propose a new office bill', expanded=False):
        with st.form('bill_new', clear_on_submit=True):
            title = st.text_input('Bill title', placeholder='The Mandatory 4 PM Chai Resolution', max_chars=90)
            details = st.text_area('Why should the house consider this?', placeholder='A concise and extremely serious case for an unserious topic…', max_chars=400)
            submit = st.form_submit_button('Table this bill', type='primary')
        if submit:
            try:
                bid = db.new_bill(user['id'],title,details)
                st.toast(f'Bill #{bid} has been tabled!')
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    all_bills = db.bills()
    if not all_bills:
        st.info('Nothing is on the floor yet. Propose the first bill!')
    for b in all_bills:
        total = b['aye']+b['no']+b['abstain']
        with st.container(border=True):
            cl, cr = st.columns([4,1])
            with cl:
                st.markdown(f"#### {e(b['title'])}")
                st.caption(f"Bill #{b['id']} · Proposed by {b['nickname']} · {day_time(b['created_at'])}")
            with cr:
                st.markdown('🟢 **OPEN**' if b['status']=='open' else '🔒 **CLOSED**')
            if b['details']:
                st.write(b['details'])
            a,n,ab = st.columns(3)
            a.metric('AYE', b['aye'])
            n.metric('NO', b['no'])
            ab.metric('ABSTAIN', b['abstain'])
            small_bar('Support',b['aye'],total)
            if b['status']=='open':
                current = db.my_vote(b['id'],user['id'])
                options=['Aye','No','Abstain']
                with st.form(f"ballot_{b['id']}"):
                    choice = st.radio(f"Your ballot · Bill #{b['id']}", options, index=options.index(current) if current else 0, horizontal=True)
                    cast = st.form_submit_button('Update my vote' if current else 'Cast my vote')
                if cast:
                    try:
                        db.vote(b['id'], user['id'], choice)
                        st.toast('Ballot recorded.')
                        st.rerun()
                    except ValueError as exc:
                        st.warning(str(exc))
                if host and st.button('Close voting and announce result', key=f"close_{b['id']}"):
                    db.close_bill(b['id'])
                    st.rerun()
            else:
                outcome = 'Passed ✅' if b['aye']>b['no'] else ('Tied 🤝' if b['aye']==b['no'] else 'Not passed ❌')
                st.success(f"Final result: {outcome} · {total} ballot(s)")
    st.caption('House rules: office-safe topics only. This voting game is unrelated to public elections or official parliamentary business.')


def board(user):
    hero('02 / Noticeboard','Good vibes, great ideas.','Appreciations, constructive suggestions, and harmless observations. Every message is reviewed before appearing.')
    st.info('This is not an anonymous whistleblowing channel. The host can see who submitted a message for moderation. Please avoid personal accusations, private information, or political content.')
    with st.expander('✍️ Write a message', expanded=False):
        with st.form('write_post', clear_on_submit=True):
            category = st.selectbox('Category',['Appreciation','Team idea','Light moment'])
            body = st.text_area('Message', max_chars=350, placeholder='Shoutout to everyone who survived three meetings and still finished the report!')
            submitted = st.form_submit_button('Send for review', type='primary')
        if submitted:
            try:
                db.add_post(user['id'],category,body)
                st.success('Sent to the host for approval. Thanks!')
            except ValueError as exc:
                st.error(str(exc))
    published = db.posts()
    if not published:
        st.caption('Your team noticeboard is empty. The first approved message will appear here.')
    for post in published:
        with st.container(border=True):
            st.caption(f"{post['category'].upper()} · {day_time(post['created_at'])} · Team contribution")
            st.write(post['body'])
            reactions = db.reactions_for(post['id'])
            cols = st.columns([1,1,1,3])
            for i,emo in enumerate(('👏','💡','😄')):
                if cols[i].button(f"{emo} {reactions.get(emo,0)}", key=f"reaction_{post['id']}_{emo}"):
                    db.react(post['id'],user['id'],emo)
                    st.rerun()


def moments(user):
    hero('03 / Live Moments','One click. Every screen.','The host can broadcast a friendly 15–120 second announcement to every open Backbench tab, with an optional celebration animation.')
    st.subheader('What your teammates will see')
    st.write('A synchronized banner appears across all connected sessions within a few seconds. It never controls the laptop outside this website.')
    recent=db.recent_moments()
    if recent:
        st.markdown('**Recent moments**')
        for m in recent[:8]:
            st.markdown(f'<div class="member-line">✦ <b>{e(m["title"])}</b> · {e(m["kind"])} <span style="float:right;color:#8faac5">{e(day_time(m["created_at"]))}</span></div>',unsafe_allow_html=True)
    else:
        st.caption('No moment has been broadcast yet. The host can launch the first one in Host Console.')


def lounge(user):
    hero('04 / Team Lounge','A room for the team.','See who has joined. No attendance monitoring, location, or device scanning.')
    users=db.members()
    online=sum(db.now()-u['last_seen'] <25 for u in users)
    a,b = st.columns(2)
    a.metric('Members',len(users)); b.metric('Active tabs',online)
    if not users:
        st.info('Nobody has joined yet.')
    for u in users:
        with st.container(border=True):
            active = db.now()-u['last_seen'] <25
            st.write(('🟢' if active else '⚪')+'  **'+u['nickname']+'** — '+('Active now' if active else 'Away'))
    st.caption('Active status uses a periodic app heartbeat. Closing the browser typically shows Away after ~25 seconds.')


def host_console(user):
    hero('Private host controls','Keep it fun. Keep it kind.','Approve noticeboard posts, trigger live moments, and close votes. The host PIN is separate from the room code.')
    post_tab, moment_tab, guidance_tab=st.tabs(['🛡️ Review messages','✨ Broadcast a moment','⚙️ Hosting tips'])
    with post_tab:
        pending=db.posts('pending')
        st.markdown(f'**{len(pending)} message(s) awaiting approval**')
        if not pending:
            st.success('All caught up.')
        for p in pending:
            with st.container(border=True):
                st.caption(f"{p['category']} · Submitted by {p['nickname']} · {day_time(p['created_at'])}")
                st.write(p['body'])
                a,b=st.columns(2)
                if a.button('Approve',key=f"approve_{p['id']}",type='primary'):
                    db.moderate_post(p['id'],'approved');st.rerun()
                if b.button('Reject',key=f"reject_{p['id']}"):
                    db.moderate_post(p['id'],'rejected');st.rerun()
    with moment_tab:
        st.markdown('**Broadcast a team moment**')
        preset={
            'Applause': ('Round of applause 👏','Someone just did something worth celebrating.'),
            'Quick Poll': ('60-second challenge','Everyone make a bold prediction before the timer ends.'),
            'Tea Break': ('Chai protocol activated ☕','Take a minute, stretch, and recharge.'),
            'Team Challenge': ('Mini team challenge ⚡','Name one tiny improvement we could try this week.'),
        }
        with st.form('send_moment'):
            kind=st.selectbox('Moment type', list(preset.keys()))
            title=st.text_input('On-screen headline',max_chars=90, placeholder='A round of applause for the team!')
            detail=st.text_area('Short message',max_chars=240, placeholder='We finished the proposal. Great work everyone.')
            duration=st.slider('Show for (seconds)',min_value=10,max_value=120,value=30,step=5)
            sent=st.form_submit_button('Broadcast to the room',type='primary')
        if sent:
            try:
                default_title,default_detail=preset[kind]
                db.add_moment(user['id'], kind,title or default_title,detail or default_detail,duration)
                st.success('Broadcast live! Other open tabs will update automatically.')
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    with guidance_tab:
        st.markdown('''**House rules**
- No relationship questions, targeting, allegations, or humiliating posts.
- No official or confidential MP-office information in the app.
- Do not present fictional votes as formal decisions.
- Keep announcements voluntary and limited to this webpage.
- Only people with the private room code should be invited.

**Security:** This local app uses a room access code and personal PINs, but it is not an enterprise identity system. Only use it on a trusted office LAN, not exposed directly to the public internet.''')


def render():
    db.init_db()
    inject_style()
    if not db.room():
        setup_room()
        st.stop()
    if 'user' not in st.session_state:
        join_room()
        st.stop()

    user=st.session_state.user
    with st.sidebar:
        st.markdown('<div class="brand">THE <span>BACKBENCH_</span></div><div class="soft">OFFICE EDITION · LIVE</div>',unsafe_allow_html=True)
        st.write('')
        st.write(f"👤 Signed in as **{user['nickname']}**")
        pages=['🏠 Home','🏛️ The House','💬 Noticeboard','✨ Live Moments','🟢 Team Lounge']
        if st.session_state.get('host',False):
            pages.append('🛡️ Host Console')
        page=st.radio('Explore',pages,key='page_selector',label_visibility='collapsed')
        st.divider()
        if not st.session_state.get('host',False):
            with st.expander('🔑 Host access'):
                pin=st.text_input('Host PIN',type='password',key='host_input')
                if st.button('Unlock host console',use_container_width=True):
                    if db.validate_host_pin(pin):
                        st.session_state.host=True
                        st.rerun()
                    else:
                        st.error('Incorrect host PIN')
        else:
            st.success('Host controls enabled')
            if st.button('Lock host controls',use_container_width=True):
                st.session_state.host=False
                st.rerun()
        st.toggle('Celebration effects',value=True,key='effects')
        if st.button('Leave room',use_container_width=True):
            st.session_state.pop('user',None)
            st.session_state.host=False
            st.rerun()
        st.caption('Local multiplayer • Refreshes every 3 seconds')

    @st.fragment(run_every='3s')
    def live_content():
        db.heartbeat(user['id'])
        moment_banner()
        if page == '🏠 Home':
            home(user)
        elif page == '🏛️ The House':
            house(user,st.session_state.get('host',False))
        elif page == '💬 Noticeboard':
            board(user)
        elif page == '✨ Live Moments':
            moments(user)
        elif page == '🟢 Team Lounge':
            lounge(user)
        elif page == '🛡️ Host Console' and st.session_state.get('host',False):
            host_console(user)
        st.divider()
        st.caption('THE BACKBENCH · For positive team fun only · India Standard Time · Not an official Parliament/MP platform')

    live_content()


if __name__ == '__main__':
    render()
