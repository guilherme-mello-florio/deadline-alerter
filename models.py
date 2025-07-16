# models.py (Minimal version for alerter)

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Base class for all models
Base = declarative_base()

# Needed for the user's name and email
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(45))

# Needed for the project's name
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String(45), unique=True)

# The primary model for querying deadlines
class ProjectScheduleTask(Base):
    __tablename__ = 'project_schedule_tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    interface_name = Column(String(255), nullable=False)
    task_name = Column(String(255), nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default='Pendente')
    responsible_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # These relationships are essential for the joinedload() in the alerter script to work
    project = relationship("Project")
    responsible_user = relationship("User")