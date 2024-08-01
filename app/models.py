from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from flask import current_app as app
from itsdangerous import URLSafeTimedSerializer as Serializer
from typing import Dict
from . import db, login_manager


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE_ARTICLES = 0x04
    MODERATE_COMMENTS = 0x08
    ADMINISTER = 0x80


class Role(db.Model):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    default: Mapped[bool] = mapped_column(default=False, index=True, nullable=True)
    permissions: Mapped[int]
    users = db.relationship('User', backref='role', lazy = 'dynamic')

    @staticmethod
    def insert_roles():
        roles = {
            'User': (Permission.FOLLOW |
                     Permission.COMMENT |
                     Permission.WRITE_ARTICLES, True),
            'Moderator': (Permission.FOLLOW |
                          Permission.COMMENT |
                          Permission.WRITE_ARTICLES |
                          Permission.MODERATE_COMMENTS, False),
            'Administrator': (0xff, False)
        }
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = roles[r][1]
            db.session.add(role)
        db.session.commit()
    
    def __repr__(self) -> str:
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))
    password_hash: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(default=False, index=True, nullable=True)
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
    
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
    def reset_password(token, new_password):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token.decode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True
    
    def generate_email_change_token(self, new_email):
        s = Serializer(app.config['SECRET_KEY'])
        return s.dumps({'change_email': self.id, 'new_email': new_email}).encode('utf-8')
        
    def change_email(self, token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            data = s.loads(token.decode('utf-8'))
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
        db.session.add(self)
        return True
    
    def can(self, permissions):
        return self.role is not None and \
            (self.role.permissions & permissions) == permissions
            
    def is_administrator(self):
        return self.can(Permission.ADMINISTER)
     
    
    def __repr__(self) -> str:
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False
    
    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))