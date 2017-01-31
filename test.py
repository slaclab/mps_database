from sqlalchemy import Table, Column, Integer, String, ForeignKey, MetaData, create_engine
from sqlalchemy.orm import relation, backref, validates, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

metadata = MetaData()
Base = declarative_base(metadata=metadata)

class Model(Base):
  __tablename__ = 'model'

  id = Column(Integer, primary_key=True)
  name = Column(String(255), nullable=False)
  parent_id = Column(Integer, ForeignKey('model.id'))
  parent = relation("Model", backref=backref('children', cascade='all', order_by=id), remote_side=[id])

  @validates('children')
  def validator(self, key, value):
    """
    Load the children collection as part of validation.
   """
#    self.children
    return value

Session = sessionmaker(expire_on_commit=False)
engine = create_engine('sqlite://')
Session.configure(bind=engine)
metadata.create_all(bind=engine)
session = Session()

model1 = Model()
model1.name = 'test1'
session.add(model1)
session.commit()

model2 = Model()
model2.name = 'test2'
model2.parent = model1
session.commit()
