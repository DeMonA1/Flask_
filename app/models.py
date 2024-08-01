from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from flask import current_app as app
from itsdangerous import URLSafeTimedSerializer as Serializer
from typing import Dict
from . import db, login_manager


class Role(db.Model):
    __tablename__ = 'roles'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    users = db.relationship('User', backref='role', lazy = 'dynamic')

    def __repr__(self) -> str:
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    username: Mapped[str] = mapped_column(unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))
    password_hash: Mapped[str]
    confirmed: Mapped[bool] = mapped_column(default=False, index=True, nullable=True)
    
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
    
    def __repr__(self) -> str:
        return '<User %r>' % self.username

    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))