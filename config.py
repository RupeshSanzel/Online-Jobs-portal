# config.py
import os

class Config:
    SECRET_KEY = 'your-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///job_portal.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False