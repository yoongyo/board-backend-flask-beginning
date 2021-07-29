from app.app import app,db


@app.route('/')
def home():
    return 'Hello, World!'

@app.route('/create')
def post_create():
    post = Post(title='title1', content="fuck...")
    db.session.add(post)
    return 'create'

@app.route('/list')
def post_list():
    Post.query.filter
    return
