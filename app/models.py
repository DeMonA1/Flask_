from __future__ import annotations
from datetime import datetime
import hashlib
from sqlalchemy.orm import Mapped, mapped_column, backref, relationship
from sqlalchemy import ForeignKey, PrimaryKeyConstraint, Integer, DateTime, String, Boolean
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app as app, url_for
from itsdangerous import URLSafeTimedSerializer as Serializer
from typing import Dict
from markdown import markdown
import bleach
from . import db, login_manager
from .exceptions import ValidationError


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    default: Mapped[bool] = mapped_column(default=False, index=True, nullable=True)
    permissions: Mapped[int]
    users = db.relationship('User', backref='role', lazy = 'dynamic')

    def __init__(self, **kwargs) -> None:
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0
    
    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT, 
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT, 
                          Permission.WRITE, Permission.MODERATE, Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()
    
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm
        
    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm
        
    def reset_permissions(self):
        self.permissions = 0
    
    def has_permission(self, perm):
        return self.permissions & perm == perm
    
    def __repr__(self) -> str:
        return '<Role %r>' % self.name


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
    followed_id = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
    timestamp = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (PrimaryKeyConstraint('follower_id', 'followed_id'),)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = mapped_column(Integer, primary_key=True)
    email = mapped_column(String, unique=True, index=True)
    username = mapped_column(String, unique=True, index=True)
    role_id = mapped_column(Integer, ForeignKey('roles.id'))
    password_hash = mapped_column(String)
    confirmed = mapped_column(Boolean, default=False, nullable=True)
    name = mapped_column(String, nullable=True)
    location = mapped_column(String, nullable=True)
    about_me = mapped_column(String, nullable=True)
    member_since = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    last_seen = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    avatar_hash = mapped_column(String, nullable=True)
    posts = relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref= backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = relationship('Comment', backref='author', lazy='dynamic')
    
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash() 
        self.follow(self)
            
    def __repr__(self) -> str:
        return '<User %r>' % self.username
    
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id) \
            .filter(Follow.follower_id == self.id)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_confirmation_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})
    
    def confirm(self, token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data: Dict = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False        
        self.confirmed = True
        db.session.add(self)
        return True
    
    def generate_reset_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'reset': self.id}).encode('utf-8')
    
    @staticmethod
    def reset_password(token: bytes, new_password):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data: Dict = s.loads(token.decode('utf-8'))
        except:
            return False
        user: User = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True
    
    def generate_email_change_token(self, new_email):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'change_email': self.id, 'new_email': new_email}).encode('utf-8')
        
    def change_email(self, token: bytes):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data: Dict = s.loads(token.decode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True
    
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)
            
    def is_administrator(self):
        return self.can(Permission.ADMIN)
     
    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
    
    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
    
    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'  
        hash = self.avatar_hash or self.gravatar_hash()
        return f'{url}/{hash}?s={size}&d={default}&r={rating}'

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)
    
    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)
    
    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(follower_id=user.id).first() is not None
    
    def generate_auth_token(self):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})
    
    @staticmethod
    def verify_auth_token(token: bytes):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])
    
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id, _external=True),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id, _external=True),
            'followed_posts_url': url_for('api.get_user_followed_posts', id=self.id, _external=True),
            'post_count': self.posts.count()
        }
        return json_user
    
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False
    
    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__ = 'posts'
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str]
    timestamp: Mapped[datetime] = mapped_column(index=True, default=datetime.utcnow)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    body_html: Mapped[str]
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    
    @staticmethod
    def on_changed_body(target: Post, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'),
            tags=allowed_tags, strip=True))

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)
    
    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),                         # without , _external=True with test_posts 
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author': url_for('api.get_user', id=self.author_id, _external=True),
            'comments': url_for('api.get_post_comments', id=self.id, _external=True),
            'comment_count': self.comments.count()
        }
        return json_post
    
db.event.listen(Post.body, 'set', Post.on_changed_body)     # events handler


class Comment(db.Model):
    __tablename__ = 'comments'
    id: Mapped[int] = mapped_column(primary_key=True)
    body: Mapped[str]
    body_html: Mapped[str]
    timestamp: Mapped[datetime] = mapped_column(index=True, default=datetime.utcnow)
    disabled: Mapped[bool] = mapped_column(nullable=True, default=False)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    post_id: Mapped[int] = mapped_column(ForeignKey('posts.id'))
    
    @staticmethod
    def on_changed_body(target: Comment, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'code', 'em', 'i', 'strong']
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html'), tags=allowed_tags, strip=True))

    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),              # without , _external=True with test_comments 
            'post_url': url_for('api.get_post', id=self.post_id, _external=True),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_id': url_for('api.get_user', id=self.author_id, _external=True),
        }
        return json_comment
    
    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)
    

db.event.listen(Comment.body, 'set', Comment.on_changed_body)