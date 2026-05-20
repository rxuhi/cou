import sqlite3
from flask import Flask, render_template, request, redirect, session, abort

app = Flask(__name__)
app.secret_key = "jeongui_high_school"

# --- DB 초기 설정 (하나로 통합) ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    # 게시글 테이블: title, password 모두 포함
    c.execute('''CREATE TABLE IF NOT EXISTS posts 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  category TEXT, title TEXT, content TEXT, mbti TEXT, password TEXT,
                  likes INTEGER DEFAULT 0, reply_count INTEGER DEFAULT 0)''')
    # 답글 테이블
    c.execute('''CREATE TABLE IF NOT EXISTS replies 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  post_id INTEGER, content TEXT, mbti TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 비속어 검열 함수 ---
def filter_text(text):
    if not text: return ""
    banned = ["나쁜말1", "나쁜말2"] # 여기에 금지어를 추가하세요
    for word in banned:
        text = text.replace(word, "♥")
    return text

# --- 라우팅 ---

@app.route('/')
def index():
    if 'mbti' not in session: return redirect('/login')
    
    cat_filter = request.args.get('cat')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    
    if cat_filter:
        posts = conn.execute("SELECT * FROM posts WHERE category = ? ORDER BY (reply_count > 0) ASC, id DESC", (cat_filter,)).fetchall()
    else:
        posts = conn.execute("SELECT * FROM posts ORDER BY (reply_count > 0) ASC, id DESC").fetchall()
    
    conn.close()
    return render_template('index.html', posts=posts, current_cat=cat_filter)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['mbti'] = request.form.get('mbti')
        return redirect('/')
    return render_template('login.html')

@app.route('/write_page')
def write_page():
    return render_template('write.html')

@app.route('/write', methods=['POST'])
def write():
    category = request.form.get('category')
    title = request.form.get('title')
    content = filter_text(request.form.get('content'))
    password = request.form.get('password')
    mbti = session.get('mbti')
    
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO posts (category, title, content, mbti, password) VALUES (?, ?, ?, ?, ?)", 
                 (category, title, content, mbti, password))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    replies = conn.execute("SELECT * FROM replies WHERE post_id = ?", (post_id,)).fetchall()
    conn.close()
    return render_template('detail.html', post=post, replies=replies)

@app.route('/reply/<int:post_id>', methods=['POST'])
def add_reply(post_id):
    content = filter_text(request.form.get('content'))
    mbti = session.get('mbti')
    conn = sqlite3.connect('database.db')
    conn.execute("INSERT INTO replies (post_id, content, mbti) VALUES (?, ?, ?)", (post_id, content, mbti))
    conn.execute("UPDATE posts SET reply_count = reply_count + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(f'/post/{post_id}')

@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    password = request.form.get('password')
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    post = conn.execute("SELECT password FROM posts WHERE id = ?", (post_id,)).fetchone()
    
    if post and post['password'] == password:
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.execute("DELETE FROM replies WHERE post_id = ?", (post_id,))
        conn.commit()
        conn.close()
        return redirect('/')
    else:
        conn.close()
        return "<script>alert('비밀번호가 틀렸습니다!'); history.back();</script>"

@app.route('/reset')
def reset():
    session.pop('mbti', None)
    return redirect('/login')

# 공감하기 로직 추가
@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    # 세션에 'liked_posts' 리스트가 없으면 새로 생성
    if 'liked_posts' not in session:
        session['liked_posts'] = []

    # 이미 공감을 누른 게시글인지 확인
    if post_id in session['liked_posts']:
        return "<script>alert('이미 공감한 글입니다!'); history.back();</script>"

    # 공감 처리
    conn = sqlite3.connect('database.db')
    conn.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    # 세션에 해당 게시글 ID 추가 (수정 가능한 리스트 처리를 위해 복사 후 저장)
    liked_list = session['liked_posts']
    liked_list.append(post_id)
    session['liked_posts'] = liked_list
    
    return redirect(f'/post/{post_id}')

if __name__ == '__main__':
    app.run(debug=True)