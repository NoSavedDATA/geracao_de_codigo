from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base, relationship, validates

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    sent_messages = relationship('Message', back_populates='sender', foreign_keys='Message.sender_id', cascade="all, delete-orphan")
    received_messages = relationship('Message', back_populates='receiver', foreign_keys='Message.receiver_id', cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    @validates('username')
    def validate_username(self, key, value):
        if not value or len(value) < 3:
            raise ValueError("Username must be at least 3 characters long.")
        return value

    @validates('email')
    def validate_email(self, key, value):
        if not value or "@" not in value:
            raise ValueError("Invalid email address.")
        return value

    @validates('password_hash')
    def validate_password(self, key, value):
        if not value or len(value) < 8:
            raise ValueError("Password hash must be at least 8 characters long.")
        return value


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sender = relationship('User', back_populates='sent_messages', foreign_keys=[sender_id])
    receiver = relationship('User', back_populates='received_messages', foreign_keys=[receiver_id])

    def __repr__(self):
        return f"<Message(id={self.id}, sender_id={self.sender_id}, receiver_id={self.receiver_id}, timestamp={self.timestamp})>"

    @validates('content')
    def validate_content(self, key, value):
        if not value or not value.strip():
            raise ValueError("Message content cannot be empty.")
        return value