# models.py (Minimal version for alerter)

from sqlalchemy import Boolean, Column, Integer, String, DateTime, ForeignKey, Boolean, Index, UniqueConstraint, Text, Date, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Base class for all models
Base = declarative_base()

task_responsible_association = Table(
    'task_responsible_association', Base.metadata,
    Column('task_id', Integer, ForeignKey('project_schedule_tasks.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

# Needed for the user's name and email
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50))
    email = Column(String(45))

    responsible_tasks = relationship(
        "ProjectScheduleTask",
        secondary=task_responsible_association,
        back_populates="responsible_users"
    )

# Needed for the project's name
class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    project_name = Column(String(45), unique=True)

# The primary model for querying deadlines
class ProjectScheduleTask(Base):
    __tablename__ = 'project_schedule_tasks'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id', ondelete="CASCADE"), nullable=False)
    interface_name = Column(String(255), nullable=False)
    drop_id = Column(Integer, ForeignKey('project_drops.id', ondelete="CASCADE"), nullable=True)
    
    task_name = Column(String(255), nullable=False) # Ex: "Entrega Técnica", "Validação Funcional"
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), default='Pendente') # Pendente, Em Andamento, Concluído
    
    responsible_users = relationship(
        "User",
        secondary=task_responsible_association,
        back_populates="responsible_tasks"
    )

    project = relationship("Project", back_populates="schedule_tasks")
    drop = relationship("ProjectDrop", back_populates="tasks")
