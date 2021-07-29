import os
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.orm import joinedload
import asyncio
import websockets
from flask_socketio import SocketIO, send, emit
import pandas as pd


basedir = os.path.abspath(os.path.dirname(__file__))
dbfile = os.path.join(basedir, 'db.sqlite')

app = Flask(__name__)
# cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
cors = CORS(app, resources={r"*": {"origins": "*"}})

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + dbfile
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Post(db.Model):
    __tablename__ = 'post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))
    comments = db.relationship('Comment', backref='post', uselist=True)
    views = db.Column(db.Integer, default=0)


class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))
    nested_comments = db.relationship('NestedComment', backref='comment', uselist=True)

class NestedComment(db.Model):
    __tablename__ = 'nestedComment'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))
    last_comments = db.relationship('LastComment', backref='nestedComment', uselist=True)

class LastComment(db.Model):
    __tablename__ = 'lastComment'
    id = db.Column(db.Integer, primary_key=True)
    nestedComment_id = db.Column(db.Integer, db.ForeignKey('nestedComment.id'))
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now().replace(microsecond=0))

class OpenGraph(db.Model):
    __tablename__ = 'open_graph'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))

db.create_all()

@app.route('/api/create', methods=['GET', 'POST'])
def post_create():
    if request.method == "POST":
        post = Post(title=request.get_json()["title"], content=request.get_json()["content"], created_at=datetime.now().replace(microsecond=0))
        db.session.add(post)
        db.session.commit()

        # 웹 소켓 사용
        return ""


@app.route('/api/post-list')
def get_post_list():
    posts = Post.query.all()
    post_list = []
    for i in posts:
        post = {
            'id': i.id,
            'title': i.title,
            'content': i.content,
            'created_at': str(i.created_at),
        }
        post_list.append(post)
    return json.dumps(post_list)

@app.route('/api/<int:post_id>')
def post_detail(post_id):
    post = Post.query.filter_by(id=post_id).first()
    post.views += 1
    db.session.commit()

    post = Post.query.filter_by(id=post_id).first()
    comments = Comment.query.filter_by(post_id=post.id).all()

    comment_list = []
    for i in comments:
        nestedComments = NestedComment.query.filter_by(comment=i).all()
        nestedComment_list = []
        for j in nestedComments:
            lastComments = LastComment.query.filter_by(nestedComment=j).all()
            lastComment_list = []
            for k in lastComments:
                lastComment = {
                    'id': k.id,
                    'content': k.content,
                    'created_at': str(k.created_at)
                }
                lastComment_list.append(lastComment)
            nestedComment = {
                'id': j.id,
                'content': j.content,
                'created_at': str(j.created_at),
                'lastComments': lastComment_list
            }
            nestedComment_list.append(nestedComment)
        comment = {
            'id': i.id,
            'content': i.content,
            'created_at': str(i.created_at),
            'nestedComments': nestedComment_list
        }
        comment_list.append(comment)

    post = {
        'id': post.id,
        'title': post.title,
        'content': post.content,
        'created_at': str(post.created_at),
        'views': post.views,
        'comments': comment_list
    }
    return json.dumps(post)

@app.route('/api/comment/<int:post_id>/comment-create', methods=['GET', 'POST'])
def comment_create(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if request.method == "POST":
        comment = Comment(post_id=post_id, post=post, content=request.get_json()["content"], created_at=datetime.now().replace(microsecond=0))

        db.session.add(comment)
        db.session.commit()

        comments = Comment.query.filter_by(post_id=post.id).all()
        comment_list = []
        for i in comments:
            nestedComments = NestedComment.query.filter_by(comment=i).all()
            nestedComment_list = []
            for j in nestedComments:
                lastComments = LastComment.query.filter_by(nestedComment=j).all()
                lastComment_list = []
                for k in lastComments:
                    lastComment = {
                        'id': k.id,
                        'content': k.content,
                        'created_at': str(k.created_at)
                    }
                    lastComment_list.append(lastComment)
                nestedComment = {
                    'id': j.id,
                    'content': j.content,
                    'created_at': str(j.created_at),
                    'lastComments': lastComment_list
                }
                nestedComment_list.append(nestedComment)
            comment = {
                'id': i.id,
                'content': i.content,
                'created_at': str(i.created_at),
                'nestedComments': nestedComment_list
            }
            comment_list.append(comment)
        return json.dumps(comment_list)

@app.route('/api/nestedComment/<int:comment_id>/nestedComment-create', methods=['GET', 'POST'])
def nested_comment_create(comment_id):
    comment = Comment.query.filter_by(id=comment_id).first()
    if request.method == "POST":
        nestedComment = NestedComment(comment_id=comment_id, comment=comment, content=request.get_json()["content"], created_at=datetime.now().replace(microsecond=0))
        db.session.add(nestedComment)
        db.session.commit()

        comments = Comment.query.filter_by(post_id=comment.post_id).all()

        comment_list = []
        for i in comments:
            nestedComments = NestedComment.query.filter_by(comment=i).all()
            nestedComment_list = []
            for j in nestedComments:
                lastComments = LastComment.query.filter_by(nestedComment=j).all()
                lastComment_list = []
                for k in lastComments:
                    lastComment = {
                        'id': k.id,
                        'content': k.content,
                        'created_at': str(k.created_at)
                    }
                    lastComment_list.append(lastComment)
                nestedComment = {
                    'id': j.id,
                    'content': j.content,
                    'created_at': str(j.created_at),
                    'lastComments': lastComment_list
                }
                nestedComment_list.append(nestedComment)
            comment = {
                'id': i.id,
                'content': i.content,
                'created_at': str(i.created_at),
                'nestedComments': nestedComment_list
            }
            comment_list.append(comment)
        return json.dumps(comment_list)


@app.route('/api/lastComment/<int:nestedComment_id>/lastComment-create', methods=['GET', 'POST'])
def last_comment_create(nestedComment_id):
    nestedComment = NestedComment.query.filter_by(id=nestedComment_id).first()
    if request.method == "POST":
        lastComment = LastComment(nestedComment=nestedComment, content=request.get_json()["content"], created_at=datetime.now().replace(microsecond=0))
        db.session.add(lastComment)
        db.session.commit()

        comment_id = nestedComment.comment_id
        comment = Comment.query.filter_by(id=comment_id).first()
        comments = Comment.query.filter_by(post_id=comment.post_id).all()

        comment_list = []
        for i in comments:
            nestedComments = NestedComment.query.filter_by(comment=i).all()
            nestedComment_list = []
            for j in nestedComments:
                lastComments = LastComment.query.filter_by(nestedComment=j).all()
                lastComment_list = []
                for k in lastComments:
                    lastComment = {
                        'id': k.id,
                        'content': k.content,
                        'created_at': str(k.created_at)
                    }
                    lastComment_list.append(lastComment)
                nestedComment = {
                    'id': j.id,
                    'content': j.content,
                    'created_at': str(j.created_at),
                    'lastComments': lastComment_list
                }
                nestedComment_list.append(nestedComment)
            comment = {
                'id': i.id,
                'content': i.content,
                'created_at': str(i.created_at),
                'nestedComments': nestedComment_list
            }
            comment_list.append(comment)
        return json.dumps(comment_list)





@socketio.on('hello')
def handle_my_custom_event(json):
    mg = send(json)
    print('received my event: ' + mg)
    # socketio.emit('my response', json, callback=messageReceived)


# @app.route('/api/getComments/<int:post_id>')
# def get_comments(post_id):
#     post = Post.query.filter_by(id=post_id).first()
#     comments = Comment.query.filter_by(post_id=post.id).all()
#
#     comment_list = []
#     for i in comments:
#         nestedComments = NestedComment.query.filter_by(comment=i).all()
#         nestedComment_list = []
#         for j in nestedComments:
#             lastComments = LastComment.query.filter_by(nestedComment=j).all()
#             lastComment_list = []
#             for k in lastComments:
#                 lastComment = {
#                     'id': k.id,
#                     'content': k.content,
#                     'created_at': str(k.created_at)
#                 }
#                 lastComment_list.append(lastComment)
#             nestedComment = {
#                 'id': j.id,
#                 'content': j.content,
#                 'created_at': str(j.created_at),
#                 'lastComments': lastComment_list
#             }
#             nestedComment_list.append(nestedComment)
#         comment = {
#             'id': i.id,
#             'content': i.content,
#             'created_at': str(i.created_at),
#             'nestedComments': nestedComment_list
#         }
#         comment_list.append(comment)
#     return json.dumps(comment_list)
#




if __name__ == '__main__':
    socketio.run(app, debug=True)
    # app.run(debug=True)