from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey
from . import db


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
    username: Mapped[str] = mapped_column(unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'))
    
    def __repr__(self) -> str:
        return '<User %r>' % self.username